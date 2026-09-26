import { useState } from 'react';

import { useAuth } from '@/auth/AuthGate';
import { Body, GhostLink, Headline, Page, PrimaryButton, Wordmark } from '@/design-system';

// Signed in, but the backend did not answer. Never guess the account state.
export default function Offline() {
  const { refresh, signOut } = useAuth();
  const [busy, setBusy] = useState(false);
  const retry = async () => {
    setBusy(true);
    await refresh();
    setBusy(false);
  };
  return (
    <Page
      actions={
        <>
          <PrimaryButton onPress={retry} disabled={busy}>
            {busy ? 'Trying…' : 'Try again'}
          </PrimaryButton>
          <GhostLink onPress={signOut}>Sign out</GhostLink>
        </>
      }
    >
      <Wordmark />
      <Headline>ElderGuard can’t connect</Headline>
      <Body>Please check Wi-Fi or mobile data. If a call feels wrong right now, hang up.</Body>
    </Page>
  );
}
