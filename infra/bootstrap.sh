#!/usr/bin/env bash
# ElderGuard GCP bootstrap. Idempotent: safe to re-run on a project that is already provisioned.
#
# Usage:
#   infra/bootstrap.sh --project my-project [--region us-central1] [--billing-account XXXXXX-XXXXXX-XXXXXX]
#                      [--budget-usd 150] [--alert-email you@example.com] [--github-repo owner/name]
#                      [--dry-run]
#
# What it does (in order): enable APIs, Firestore (nam5, PITR, TTL, weekly export), runtime service
# account with least-privilege roles, Secret Manager secrets (empty; you add versions), Artifact
# Registry, Cloud Scheduler SA + jobs, logging exclusions, uptime check + alert policies, billing
# budget + Pub/Sub topic, the budget-killswitch function, Workload Identity Federation for GitHub
# Actions, and finally prints the CNAME target for Cloudflare.
#
# Console-only steps this script cannot do (printed as a checklist at the end):
#   1. Firebase: add the project to Firebase and enable Phone sign-in.
#   2. Firebase Auth: SMS region policy allow-list = US only.
#   3. Firebase App Check (or reCAPTCHA Enterprise SMS defense) for phone auth.
#   4. Apple: APNs key uploaded to Firebase Cloud Messaging.
#   5. Anthropic console: organization spend limit (about $100 at launch) and 80% alert.
#   6. Twilio console: auto-recharge OFF; then run infra/scripts/twilio_setup.py.
#   7. Cloudflare DNS: CNAME api.getelderguard.org -> the target printed at the end.
#   8. Secret versions: run the `gcloud secrets versions add` commands printed below, piping each
#      value from a file or password manager. Never type a secret on the command line.
#
# Nothing here reads or prints a secret value.

set -euo pipefail

PROJECT=""
REGION="us-central1"
BILLING_ACCOUNT=""
BUDGET_USD="150"
ALERT_EMAIL=""
GITHUB_REPO=""
DRY_RUN=0
SERVICE="elderguard-api"
API_HOST="api.getelderguard.org"

usage() {
  sed -n '2,25p' "$0"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --billing-account) BILLING_ACCOUNT="$2"; shift 2 ;;
    --budget-usd) BUDGET_USD="$2"; shift 2 ;;
    --alert-email) ALERT_EMAIL="$2"; shift 2 ;;
    --github-repo) GITHUB_REPO="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage 1 ;;
  esac
done

[[ -n "$PROJECT" ]] || { echo "--project is required" >&2; usage 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_SA="${SERVICE}@${PROJECT}.iam.gserviceaccount.com"
SCHEDULER_SA="elderguard-scheduler@${PROJECT}.iam.gserviceaccount.com"
DEPLOY_SA="elderguard-deploy@${PROJECT}.iam.gserviceaccount.com"
KILLSWITCH_SA="elderguard-killswitch@${PROJECT}.iam.gserviceaccount.com"
EXPORT_BUCKET="gs://${PROJECT}-firestore-exports"
VOICE_BUCKET="gs://${PROJECT}-voice-templates"
AR_REPO="elderguard"
BUDGET_TOPIC="billing-budget"

# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
log() { printf '\n==> %s\n' "$*"; }

# run: execute a command, or print it in dry-run mode. Every state-changing call goes through here.
run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '   [dry-run] %q' "$1"; shift
    for a in "$@"; do printf ' %q' "$a"; done
    printf '\n'
  else
    "$@"
  fi
}

# probe: a read-only check that decides whether a create step is needed. In dry-run it always
# reports "absent" so every create command is printed and gcloud is never invoked.
probe() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return 1
  fi
  "$@" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------------------------
# 1. project + APIs
# ---------------------------------------------------------------------------------------------
log "Project ${PROJECT} in ${REGION}"
run gcloud config set project "$PROJECT"

if [[ -n "$BILLING_ACCOUNT" ]]; then
  run gcloud billing projects link "$PROJECT" --billing-account="$BILLING_ACCOUNT"
fi

log "Enable APIs"
run gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  pubsub.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  firebase.googleapis.com \
  fcm.googleapis.com \
  identitytoolkit.googleapis.com \
  billingbudgets.googleapis.com \
  eventarc.googleapis.com \
  --project="$PROJECT"

# ---------------------------------------------------------------------------------------------
# 2. Firestore: nam5, PITR, TTL, weekly export
# ---------------------------------------------------------------------------------------------
log "Firestore (nam5, PITR on)"
if probe gcloud firestore databases describe --database='(default)' --project="$PROJECT"; then
  echo "   database exists"
else
  run gcloud firestore databases create \
    --database='(default)' --location=nam5 --type=firestore-native \
    --enable-pitr --delete-protection --project="$PROJECT"
fi
run gcloud firestore databases update --database='(default)' --enable-pitr --project="$PROJECT"

log "Firestore TTL policies"
for spec in "sessions:expire_at" "usage_events:expire_at"; do
  coll="${spec%%:*}"; field="${spec##*:}"
  if probe gcloud firestore fields ttls list --collection-group="$coll" --project="$PROJECT" \
      --format='value(name)' --filter="name~${field}"; then
    echo "   ttl on ${coll}.${field} exists"
  else
    run gcloud firestore fields ttls update "$field" --collection-group="$coll" \
      --enable-ttl --project="$PROJECT" --async
  fi
done

log "Firestore rules and indexes (firebase CLI)"
run firebase deploy --only firestore:rules,firestore:indexes --project "$PROJECT" \
  --config "${HERE}/firebase.json" --non-interactive

log "Weekly Firestore export bucket + schedule"
if probe gcloud storage buckets describe "$EXPORT_BUCKET" --project="$PROJECT"; then
  echo "   bucket exists"
else
  run gcloud storage buckets create "$EXPORT_BUCKET" --location="$REGION" \
    --uniform-bucket-level-access --public-access-prevention --project="$PROJECT"
fi
run gcloud storage buckets update "$EXPORT_BUCKET" \
  --lifecycle-file="${HERE}/monitoring/export-bucket-lifecycle.json" --project="$PROJECT"
if probe gcloud firestore backups schedules list --database='(default)' --project="$PROJECT" \
    --format='value(name)' --filter='weeklyRecurrence:*'; then
  echo "   weekly backup schedule exists"
else
  run gcloud firestore backups schedules create --database='(default)' \
    --recurrence=weekly --day-of-week=SUN --retention=5w --project="$PROJECT"
fi

log "Private bucket for guardian voice template clips"
if probe gcloud storage buckets describe "$VOICE_BUCKET" --project="$PROJECT"; then
  echo "   bucket exists"
else
  run gcloud storage buckets create "$VOICE_BUCKET" --location="$REGION" \
    --uniform-bucket-level-access --public-access-prevention --project="$PROJECT"
fi

# ---------------------------------------------------------------------------------------------
# 3. Service accounts and least-privilege roles
# ---------------------------------------------------------------------------------------------
ensure_sa() {
  local email="$1" name="$2" display="$3"
  if probe gcloud iam service-accounts describe "$email" --project="$PROJECT"; then
    echo "   ${email} exists"
  else
    run gcloud iam service-accounts create "$name" --display-name="$display" --project="$PROJECT"
  fi
}

log "Runtime service account (${RUNTIME_SA})"
ensure_sa "$RUNTIME_SA" "$SERVICE" "ElderGuard API runtime"
# Exactly the roles in docs/ARCHITECTURE.md. Secret access is granted per secret below;
# bucket access is granted on the one bucket, not project-wide.
for role in roles/datastore.user roles/firebasecloudmessaging.admin roles/logging.logWriter; do
  run gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${RUNTIME_SA}" --role="$role" --condition=None --quiet
done
run gcloud storage buckets add-iam-policy-binding "$VOICE_BUCKET" \
  --member="serviceAccount:${RUNTIME_SA}" --role=roles/storage.objectAdmin

log "Scheduler service account (${SCHEDULER_SA})"
ensure_sa "$SCHEDULER_SA" "elderguard-scheduler" "Cloud Scheduler caller for /internal"
run gcloud run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
  --member="serviceAccount:${SCHEDULER_SA}" --role=roles/run.invoker --project="$PROJECT" || true

log "Kill-switch function service account (${KILLSWITCH_SA})"
ensure_sa "$KILLSWITCH_SA" "elderguard-killswitch" "Budget kill switch"
run gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${KILLSWITCH_SA}" --role=roles/datastore.user --condition=None --quiet

# ---------------------------------------------------------------------------------------------
# 4. Secrets (created empty; the operator adds versions from a file or pipe)
# ---------------------------------------------------------------------------------------------
log "Secret Manager secrets"
SECRETS=(ANTHROPIC_API_KEY STT_API_KEY TWILIO_AUTH_TOKEN PHONE_HASH_PEPPER STREAM_TOKEN_SECRET SENTRY_DSN)
for s in "${SECRETS[@]}"; do
  if probe gcloud secrets describe "$s" --project="$PROJECT"; then
    echo "   ${s} exists"
  else
    run gcloud secrets create "$s" --replication-policy=automatic --project="$PROJECT"
  fi
  run gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor \
    --project="$PROJECT" --quiet
done
# The kill switch needs the Twilio token to repoint the number.
run gcloud secrets add-iam-policy-binding TWILIO_AUTH_TOKEN \
  --member="serviceAccount:${KILLSWITCH_SA}" --role=roles/secretmanager.secretAccessor \
  --project="$PROJECT" --quiet

# ---------------------------------------------------------------------------------------------
# 5. Artifact Registry
# ---------------------------------------------------------------------------------------------
log "Artifact Registry repo ${AR_REPO}"
if probe gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" --project="$PROJECT"; then
  echo "   repo exists"
else
  run gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
    --location="$REGION" --project="$PROJECT"
fi

# ---------------------------------------------------------------------------------------------
# 6. Cloud Run service (first deploy uses a placeholder image so IAM and URL exist)
# ---------------------------------------------------------------------------------------------
log "Cloud Run service ${SERVICE} (spec: infra/cloudrun.yaml)"
echo "   The real image is deployed by .github/workflows/deploy.yml. This step only makes sure"
echo "   the service exists so the scheduler and uptime check have a URL."
SERVICE_URL="https://${SERVICE}-PLACEHOLDER-${REGION}.a.run.app"
if probe gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT"; then
  SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT" \
    --format='value(status.url)')"
  echo "   service exists at ${SERVICE_URL}"
else
  echo "   service not deployed yet; run deploy.yml, then re-run bootstrap for scheduler + uptime"
fi

# ---------------------------------------------------------------------------------------------
# 7. Cloud Scheduler jobs -> /internal/* with OIDC
# ---------------------------------------------------------------------------------------------
log "Cloud Scheduler jobs"
ensure_job() {
  local name="$1" schedule="$2" path="$3"
  local uri="${SERVICE_URL}${path}"
  if probe gcloud scheduler jobs describe "$name" --location="$REGION" --project="$PROJECT"; then
    run gcloud scheduler jobs update http "$name" --location="$REGION" --project="$PROJECT" \
      --schedule="$schedule" --time-zone="America/Los_Angeles" --uri="$uri" \
      --http-method=POST --oidc-service-account-email="$SCHEDULER_SA" \
      --oidc-token-audience="$SERVICE_URL" --attempt-deadline=120s
  else
    run gcloud scheduler jobs create http "$name" --location="$REGION" --project="$PROJECT" \
      --schedule="$schedule" --time-zone="America/Los_Angeles" --uri="$uri" \
      --http-method=POST --oidc-service-account-email="$SCHEDULER_SA" \
      --oidc-token-audience="$SERVICE_URL" --attempt-deadline=120s
  fi
}
ensure_job "elderguard-sweep" "* * * * *" "/internal/sweep"
ensure_job "elderguard-rollup" "10 2 * * *" "/internal/rollup"

# ---------------------------------------------------------------------------------------------
# 8. Logging: exclusions so per-frame noise and PII never land in Cloud Logging
# ---------------------------------------------------------------------------------------------
log "Cloud Logging exclusion filters"
ensure_exclusion() {
  local name="$1" filter="$2" desc="$3"
  if probe gcloud logging sinks describe _Default --project="$PROJECT" --format='value(exclusions)' \
      --filter="exclusions.name=${name}"; then
    run gcloud logging sinks update _Default --project="$PROJECT" \
      --update-exclusion="name=${name},filter=${filter}"
  else
    run gcloud logging sinks update _Default --project="$PROJECT" \
      --add-exclusion="name=${name},filter=${filter},description=${desc}"
  fi
}
ensure_exclusion "elderguard-low-severity" \
  "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE}\" AND severity<INFO" \
  "Drop DEBUG from the API in prod"
ensure_exclusion "elderguard-pii-fields" \
  "resource.type=\"cloud_run_revision\" AND (jsonPayload.transcript:* OR jsonPayload.window_text:* OR jsonPayload.partial_text:* OR jsonPayload.from_number:* OR jsonPayload.phone:* OR jsonPayload.From:*)" \
  "Belt and braces: never store transcript or phone fields even if redaction regresses"
run gcloud logging buckets update _Default --location=global --retention-days=30 --project="$PROJECT"

# ---------------------------------------------------------------------------------------------
# 9. Monitoring: notification channel, uptime check, alert policies
# ---------------------------------------------------------------------------------------------
log "Cloud Monitoring"
CHANNEL_NAME=""
if [[ -n "$ALERT_EMAIL" ]]; then
  if [[ "$DRY_RUN" -eq 0 ]]; then
    CHANNEL_NAME="$(gcloud alpha monitoring channels list --project="$PROJECT" \
      --filter="type=email AND labels.email_address=${ALERT_EMAIL}" --format='value(name)' | head -n1 || true)"
  fi
  if [[ -z "$CHANNEL_NAME" ]]; then
    run gcloud alpha monitoring channels create --project="$PROJECT" \
      --display-name="ElderGuard operator" --type=email \
      --channel-labels="email_address=${ALERT_EMAIL}"
    CHANNEL_NAME="projects/${PROJECT}/notificationChannels/PLACEHOLDER"
  fi
else
  echo "   --alert-email not given; policies are created without a notification channel"
fi

log "Uptime check on /health from three regions"
UPTIME_HOST="${SERVICE_URL#https://}"
if probe gcloud monitoring uptime list-configs --project="$PROJECT" --format='value(name)' \
    --filter='displayName="ElderGuard /health"'; then
  echo "   uptime check exists"
else
  run gcloud monitoring uptime create "ElderGuard /health" --project="$PROJECT" \
    --resource-type=uptime-url --resource-labels="host=${UPTIME_HOST},project_id=${PROJECT}" \
    --protocol=https --path=/health --port=443 --period=5 --timeout=10 \
    --regions=usa-oregon,usa-virginia,europe
fi

log "Log-based metrics (infra/monitoring/log-metrics.json)"
while IFS=$'\t' read -r mname mdesc mfilter; do
  mfilter="${mfilter//__SERVICE__/${SERVICE}}"
  if probe gcloud logging metrics describe "$mname" --project="$PROJECT"; then
    run gcloud logging metrics update "$mname" --project="$PROJECT" \
      --description="$mdesc" --log-filter="$mfilter"
  else
    run gcloud logging metrics create "$mname" --project="$PROJECT" \
      --description="$mdesc" --log-filter="$mfilter"
  fi
done < <(python3 -c '
import json, sys
for k, v in json.load(open(sys.argv[1])).items():
    print(k, v["description"], v["filter"], sep="\t")
' "${HERE}/monitoring/log-metrics.json")

log "Alert policies (infra/monitoring/alerts/*.json)"
for f in "${HERE}"/monitoring/alerts/*.json; do
  name="$(basename "$f" .json)"
  rendered="$(mktemp)"
  sed -e "s#__PROJECT__#${PROJECT}#g" -e "s#__SERVICE__#${SERVICE}#g" \
      -e "s#__CHANNEL__#${CHANNEL_NAME}#g" "$f" > "$rendered"
  if [[ -z "$CHANNEL_NAME" ]]; then
    python3 - "$rendered" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d.pop("notificationChannels", None)
json.dump(d, open(p, "w"))
PY
  fi
  if probe gcloud alpha monitoring policies list --project="$PROJECT" --format='value(name)' \
      --filter="displayName=\"$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["displayName"])' "$rendered")\""; then
    echo "   policy ${name} exists (edit in console or delete to recreate)"
  else
    run gcloud alpha monitoring policies create --project="$PROJECT" --policy-from-file="$rendered"
  fi
  rm -f "$rendered"
done

# ---------------------------------------------------------------------------------------------
# 10. Billing budget -> Pub/Sub -> kill switch function
# ---------------------------------------------------------------------------------------------
log "Pub/Sub topic ${BUDGET_TOPIC}"
if probe gcloud pubsub topics describe "$BUDGET_TOPIC" --project="$PROJECT"; then
  echo "   topic exists"
else
  run gcloud pubsub topics create "$BUDGET_TOPIC" --project="$PROJECT"
fi

if [[ -n "$BILLING_ACCOUNT" ]]; then
  log "Billing budget \$${BUDGET_USD}/month with 50/90/100% alerts"
  if probe gcloud billing budgets list --billing-account="$BILLING_ACCOUNT" --format='value(name)' \
      --filter='displayName="ElderGuard monthly"'; then
    echo "   budget exists"
  else
    run gcloud billing budgets create --billing-account="$BILLING_ACCOUNT" \
      --display-name="ElderGuard monthly" --budget-amount="${BUDGET_USD}USD" \
      --filter-projects="projects/${PROJECT}" \
      --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
      --notifications-rule-pubsub-topic="projects/${PROJECT}/topics/${BUDGET_TOPIC}" \
      --notifications-rule-monitoring-notification-channels="${CHANNEL_NAME}"
  fi
else
  echo "   --billing-account not given; skipping budget creation (topic is ready for it)"
fi

log "Deploy budget-killswitch function"
run gcloud functions deploy budget-killswitch --gen2 --region="$REGION" --project="$PROJECT" \
  --runtime=python312 --source="${HERE}/functions/budget-killswitch" --entry-point=on_budget \
  --trigger-topic="$BUDGET_TOPIC" --service-account="$KILLSWITCH_SA" \
  --set-env-vars="GCP_PROJECT=${PROJECT},TWILIO_ACCOUNT_SID=REPLACE_ME,TWILIO_GUARDIAN_NUMBER=REPLACE_ME,FALLBACK_TWIML_URL=REPLACE_ME" \
  --set-secrets="TWILIO_AUTH_TOKEN=TWILIO_AUTH_TOKEN:latest" \
  --memory=256Mi --max-instances=1 --no-allow-unauthenticated

# ---------------------------------------------------------------------------------------------
# 11. Workload Identity Federation for GitHub Actions (no JSON keys, ever)
# ---------------------------------------------------------------------------------------------
if [[ -n "$GITHUB_REPO" ]]; then
  log "Workload Identity Federation for ${GITHUB_REPO}"
  ensure_sa "$DEPLOY_SA" "elderguard-deploy" "GitHub Actions deployer"
  for role in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
    run gcloud projects add-iam-policy-binding "$PROJECT" \
      --member="serviceAccount:${DEPLOY_SA}" --role="$role" --condition=None --quiet
  done
  if probe gcloud iam workload-identity-pools describe github --location=global --project="$PROJECT"; then
    echo "   pool exists"
  else
    run gcloud iam workload-identity-pools create github --location=global \
      --display-name="GitHub Actions" --project="$PROJECT"
  fi
  if probe gcloud iam workload-identity-pools providers describe github-oidc \
      --workload-identity-pool=github --location=global --project="$PROJECT"; then
    echo "   provider exists"
  else
    run gcloud iam workload-identity-pools providers create-oidc github-oidc \
      --workload-identity-pool=github --location=global --project="$PROJECT" \
      --issuer-uri="https://token.actions.githubusercontent.com" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
      --attribute-condition="assertion.repository == '${GITHUB_REPO}'"
  fi
  PROJECT_NUMBER="PROJECT_NUMBER"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  fi
  run gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --project="$PROJECT" \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}"
  echo "   GitHub repo variables to set:"
  echo "     GCP_PROJECT=${PROJECT}"
  echo "     GCP_REGION=${REGION}"
  echo "     WIF_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-oidc"
  echo "     DEPLOY_SA=${DEPLOY_SA}"
fi

# ---------------------------------------------------------------------------------------------
# 12. Domain mapping target for Cloudflare
# ---------------------------------------------------------------------------------------------
log "Custom domain ${API_HOST}"
if probe gcloud beta run domain-mappings describe --domain="$API_HOST" --region="$REGION" --project="$PROJECT"; then
  echo "   mapping exists"
else
  run gcloud beta run domain-mappings create --service="$SERVICE" --domain="$API_HOST" \
    --region="$REGION" --project="$PROJECT"
fi

cat <<EOF

=====================================================================================
DONE. Remaining steps are console-only or need a human with the secret in hand.
=====================================================================================

Secrets: add one version each, piping the value from a file or a password manager.
  for s in ${SECRETS[*]}; do
    gcloud secrets versions add \$s --project=${PROJECT} --data-file=/path/to/\$s.txt
  done
  Or from a pipe:   op read 'op://vault/item/field' | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
  PHONE_HASH_PEPPER and STREAM_TOKEN_SECRET:  python3 -c 'import secrets; print(secrets.token_hex(32))' | gcloud secrets versions add NAME --data-file=-

Cloudflare DNS: create a CNAME
  ${API_HOST}  ->  ghs.googlehosted.com   (proxy status: DNS only, or proxied; WebSockets pass either way)
  Confirm the exact target with:  gcloud beta run domain-mappings describe --domain=${API_HOST} --region=${REGION}

Console checklist:
  [ ] Firebase console: add project, enable Authentication > Phone.
  [ ] Firebase Auth > Settings > SMS region policy: allow United States only.
  [ ] Firebase App Check for the iOS and Android apps (M2) or reCAPTCHA Enterprise SMS defense now.
  [ ] Firebase Cloud Messaging: upload the APNs key (M2).
  [ ] Anthropic console: set the organization spend limit (about \$100) and an 80% alert.
  [ ] Twilio console: turn auto-recharge OFF. Then:  python3 infra/scripts/twilio_setup.py --project ${PROJECT}
  [ ] Function env: set TWILIO_ACCOUNT_SID, TWILIO_GUARDIAN_NUMBER, FALLBACK_TWIML_URL on budget-killswitch
      (twilio_setup.py prints the Bin URL).
  [ ] Sentry: create the project and add SENTRY_DSN as a secret version.
  [ ] Deepgram console: lower the project's concurrency / usage limit.
  [ ] Deploy: run .github/workflows/deploy.yml, then re-run this script so the scheduler and
      uptime check point at the real service URL.
EOF
