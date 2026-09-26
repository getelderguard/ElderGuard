import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { CONSENT_VERSION, enroll } from '@/api/accounts';
import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthGate';
import { Body, Card, EG_TOKENS, Eyebrow, GhostLink, Headline, Page, PrimaryButton } from '@/design-system';

// Consent text, version CONSENT_VERSION. Changing any sentence here means a new version in both
// this app (src/api/accounts.ts) and the backend (CONSENT_VERSION), so everyone re-consents.
// Draft pending counsel review (docs/LEGAL.md); no user beyond the maintainer until then.
const POINTS = [
  'When you tap “Check this call”, your phone calls the ElderGuard line and you merge it into your call. ElderGuard then hears you and the other person.',
  'ElderGuard tells everyone on the call that the call is protected by ElderGuard.',
  'A computer turns the voices into text and checks it for signs of a scam. Nothing is recorded, and the words are not saved.',
  'ElderGuard keeps the warning level for each call for 30 days, so you and your family can look back.',
  'To do this, ElderGuard uses Twilio for the phone line, Deepgram to turn speech into text, Anthropic to check for scams, and Google to sign you in and store your account.',
  'ElderGuard can be wrong. If a call feels wrong, hang up, even if ElderGuard has not warned you.',
  'You can delete your account and everything in it at any time.',
];

function explain(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return 'ElderGuard is invite-only for now, and this phone number is not on the list yet.';
    if (e.status === 409 && e.message.includes('consent')) return 'Please update the ElderGuard app, then try again.';
    if (e.status === 409) return 'This phone number is already set up with ElderGuard.';
    if (e.status === 429) return 'Too many tries. Please wait a minute and try again.';
  }
  return 'ElderGuard could not finish setting up. Please check your connection and try again.';
}

export default function Consent() {
  const { displayName, nickname } = useLocalSearchParams<{ displayName: string; nickname: string }>();
  const { refresh } = useAuth();
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const agree = async () => {
    if (busy || !displayName) return;
    setBusy(true);
    setProblem(null);
    try {
      await enroll(displayName, nickname || 'Mom');
      await refresh();
    } catch (e) {
      setProblem(explain(e));
      setBusy(false);
    }
  };

  return (
    <Page
      actions={
        <>
          {problem && (
            <View accessibilityLiveRegion="polite">
              <Body style={{ color: EG_TOKENS.alert }}>{problem}</Body>
            </View>
          )}
          <PrimaryButton onPress={agree} disabled={busy || !displayName}>
            {busy ? 'Setting up…' : 'I agree'}
          </PrimaryButton>
          <GhostLink onPress={() => router.back()}>Back</GhostLink>
        </>
      }
    >
      <Headline>Before ElderGuard listens</Headline>
      <Card>
        <View style={{ gap: 14 }}>
          {POINTS.map((p) => (
            <Body key={p}>{p}</Body>
          ))}
        </View>
      </Card>
      <Eyebrow>Version {CONSENT_VERSION}</Eyebrow>
    </Page>
  );
}
