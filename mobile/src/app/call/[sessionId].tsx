import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Body, BrassDial, EG_TOKENS, Headline, PrimaryButton, SecondaryButton, Shield, Wordmark } from '@/design-system';
import { TIER_COPY } from '@/session/copy';
import { useLiveSession } from '@/session/useLiveSession';

export default function CallScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const { session, stale, error } = useLiveSession(sessionId);
  const gaveUp = useMergeTimeout(session?.state);

  const goHome = () => router.dismissTo('/');

  if (gaveUp || session?.state === 'ended' || session?.state === 'expired') {
    const neverJoined = gaveUp || session?.state === 'expired' || session?.live_at == null;
    return (
      <Screen>
        <View style={{ gap: 12 }}>
          <Wordmark size={22} />
          <Headline>{neverJoined ? 'ElderGuard did not join' : 'The call has ended'}</Headline>
          <Body>
            {neverJoined
              ? 'The merge did not happen, so ElderGuard could not listen. You can try again on your next call.'
              : 'Thank you for checking. If anything still feels wrong, call someone you trust.'}
          </Body>
        </View>
        <PrimaryButton onPress={goHome}>Done</PrimaryButton>
      </Screen>
    );
  }

  const live = session?.state === 'live' || session?.state === 'reconnecting';
  // Never show a tier we cannot vouch for: lost contact means "stale", not the last known tier.
  const lostContact = stale || (live && error !== null);
  const key = !live ? 'connecting' : lostContact ? 'stale' : (session?.tier ?? 'unknown');
  const copy = TIER_COPY[key];
  const tier = !live || lostContact ? 'unknown' : (session?.tier ?? 'unknown');
  const danger = key === 'stop';

  return (
    <Screen danger={danger}>
      <View style={{ gap: 20, alignItems: 'center' }}>
        <Wordmark size={22} />
        {live ? (
          <BrassDial value={lostContact ? 0 : (session?.dial ?? 0)} tier={tier} size={240} />
        ) : (
          <Shield size={88} />
        )}
        <View style={{ gap: 12, alignSelf: 'stretch' }} accessibilityLiveRegion="assertive">
          <Headline style={danger ? { color: EG_TOKENS.alert } : undefined}>{copy.title}</Headline>
          <Body>{copy.body}</Body>
        </View>
      </View>
      <SecondaryButton onPress={goHome}>Leave this screen</SecondaryButton>
    </Screen>
  );
}

// The intent expires on the server after 60 s. If the line never answered, stop waiting on our
// side too instead of leaving her on "Waiting for the merge".
const MERGE_WAIT_MS = 90_000;

function useMergeTimeout(state: string | undefined): boolean {
  const [expired, setExpired] = useState(false);
  const waiting = state === undefined || state === 'pending';
  useEffect(() => {
    if (!waiting) return;
    const t = setTimeout(() => setExpired(true), MERGE_WAIT_MS);
    return () => clearTimeout(t);
  }, [waiting]);
  return waiting && expired;
}

function Screen({ children, danger }: { children: React.ReactNode; danger?: boolean }) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: danger ? EG_TOKENS.alertWash : EG_TOKENS.sand }}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 24, gap: 28, justifyContent: 'space-between' }}>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
