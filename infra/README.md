# infra/

Everything needed to stand ElderGuard up on a fresh GCP project. No Terraform: at this scale it is
a dozen resources, and the parts Terraform cannot do (Firebase phone auth, APNs key) are exactly
the ones that need a human anyway. `bootstrap.sh` is the source of truth for provisioning; the
contract it implements is [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

Nothing in this directory contains or reads a secret value.

## Files

| Path | What it is |
|---|---|
| `bootstrap.sh` | Idempotent provisioning. `--dry-run` prints every command without calling gcloud. |
| `cloudrun.yaml` | The `elderguard-api` service spec. Secrets are mounted by name from Secret Manager. Applied by `deploy.yml`. |
| `firestore.rules` | Deny-by-default rules. Clients read their own account and sessions and write their own device token. |
| `firestore.indexes.json` | Composite indexes the session store queries need. |
| `firebase.json` | Points the Firebase CLI at the rules and indexes, and configures the emulator for tests. |
| `rules-test/` | `node --test` suite for the rules, run against the Firestore emulator. |
| `monitoring/log-metrics.json` | Log-based metrics derived from the backend's structured log events. |
| `monitoring/alerts/*.json` | Alert policies. `__PROJECT__`, `__SERVICE__`, `__CHANNEL__` are substituted by the script. |
| `monitoring/export-bucket-lifecycle.json` | Deletes Firestore exports after 60 days. |
| `scripts/twilio_setup.py` | Points the Guardian Line at the backend, creates the fallback TwiML Bin and usage triggers. |
| `scripts/set_provider.py` | Switch a capability's provider or flip the kill switch. Writes `config_history`. |
| `scripts/set_flag.py` | Flip a feature flag. Writes `config_history`. |
| `scripts/grant_staff.py` | Set the `staff` custom claim that unlocks `/admin/usage`. |
| `scripts/rotate_secret.sh` | Add a secret version from stdin and disable older ones. Refuses a TTY. |
| `functions/budget-killswitch/` | Pub/Sub function: at 100% of budget, set the kill switch and repoint the Twilio number. |

## Order of operations on a fresh project

1. Create the GCP project and attach billing in the console. Add it to Firebase.
2. `gcloud auth login` and `firebase login` as yourself.
3. Dry run, read the output, then run for real:

   ```bash
   infra/bootstrap.sh --project PROJECT --billing-account XXXXXX-XXXXXX-XXXXXX \
     --alert-email you@example.com --github-repo getelderguard/ElderGuard --dry-run
   infra/bootstrap.sh --project PROJECT --billing-account XXXXXX-XXXXXX-XXXXXX \
     --alert-email you@example.com --github-repo getelderguard/ElderGuard
   ```

4. Add secret versions. Pipe from a file or a password manager; never type a value:

   ```bash
   python3 -c 'import secrets; print(secrets.token_hex(32))' | gcloud secrets versions add PHONE_HASH_PEPPER --data-file=-
   python3 -c 'import secrets; print(secrets.token_hex(32))' | gcloud secrets versions add STREAM_TOKEN_SECRET --data-file=-
   gcloud secrets versions add ANTHROPIC_API_KEY --data-file=/path/to/key.txt
   gcloud secrets versions add STT_API_KEY --data-file=/path/to/key.txt
   gcloud secrets versions add TWILIO_AUTH_TOKEN --data-file=/path/to/token.txt
   gcloud secrets versions add SENTRY_DSN --data-file=/path/to/dsn.txt
   ```

5. Edit `cloudrun.yaml`: replace `REPLACE_WITH_TWILIO_ACCOUNT_SID` and `+10000000000`. The account SID and the Guardian Line number are not secrets. `deploy.yml` refuses to run while placeholders remain.
6. Set the GitHub repository variables the script printed (`GCP_PROJECT`, `GCP_REGION`, `WIF_PROVIDER`, `DEPLOY_SA`) and create a `production` environment.
7. Push a `v*` tag or run the `deploy` workflow. It builds, pushes, applies the spec, sends a canary share to the new revision, smoke-tests `/ready`, then promotes to 100%.
8. **Allow unauthenticated invocation of the service.** Twilio and the app reach Cloud Run with no Google identity; every route does its own auth (Twilio signature, stream token, Firebase ID token, scheduler OIDC). This binding is deliberately not automated so it is a conscious step:

   ```bash
   gcloud run services add-iam-policy-binding elderguard-api --region=REGION --project=PROJECT \
     --member=allUsers --role=roles/run.invoker
   ```

9. Re-run `bootstrap.sh` once so the scheduler jobs and uptime check point at the real service URL.
10. Cloudflare DNS: `CNAME api.getelderguard.org -> ghs.googlehosted.com`. Confirm with `gcloud beta run domain-mappings describe`.
11. Twilio: turn auto-recharge off in the console, then:

    ```bash
    python3 infra/scripts/twilio_setup.py --base-url https://api.getelderguard.org
    ```

    Set `FALLBACK_TWIML_URL`, `TWILIO_ACCOUNT_SID`, `TWILIO_GUARDIAN_NUMBER` on the `budget-killswitch` function from its output.
12. Work through the console checklist the script prints.

## Console-only checklist

- Firebase Authentication: enable Phone sign-in.
- Firebase Authentication settings: SMS region policy allow-list, United States only.
- Firebase App Check for the mobile apps (M2), or reCAPTCHA Enterprise SMS defense now.
- Firebase Cloud Messaging: upload the APNs key (M2).
- Anthropic console: organization spend limit (about $100 at launch) and an 80% alert.
- Twilio console: auto-recharge OFF, low-balance email notification on.
- Deepgram console: lower the project's usage limit.
- Sentry: create the project; add `SENTRY_DSN` as a secret version.

## Day-two operations

```bash
infra/scripts/set_provider.py --project PROJECT --show
infra/scripts/set_provider.py --project PROJECT scorer anthropic claude-sonnet-5 --fallback gemini
infra/scripts/set_provider.py --project PROJECT --kill-switch on      # and off again
infra/scripts/set_flag.py --project PROJECT announcement off
infra/scripts/grant_staff.py --project PROJECT FIREBASE_UID
cat new.txt | infra/scripts/rotate_secret.sh --project PROJECT ANTHROPIC_API_KEY
```

The Python scripts need `google-cloud-firestore`, `firebase-admin`, and `twilio` in whatever
environment you run them from (`uv pip install` into `backend/.venv` works). They import the
backend's config models so a typo cannot write a config the service will reject.

## Log events the alerts depend on

`monitoring/log-metrics.json` counts these structured log events from the backend. If a name
changes in code, change it here in the same commit: `inbound_accepted`, `media_started`,
`no_audio`, `score`, `scorer_failed`, `scoring_stalled`.

## Testing without a project

```bash
bash infra/bootstrap.sh --dry-run --project demo
cd infra/rules-test && npm install && npm test      # needs Java and firebase-tools
```
