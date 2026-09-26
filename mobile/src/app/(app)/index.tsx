import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiAuthMissing } from '@/api/auth';
import { ApiError } from '@/api/client';
import { createIntent } from '@/api/sessions';
import { Body, EG_TOKENS, Headline, PrimaryButton, SecondaryButton, Shield, Wordmark } from '@/design-system';
import { dialGuardianLine, isGuardianLineNumber } from '@/session/dial';

function explain(e: unknown): string {
  if (e instanceof ApiAuthMissing) return 'Please sign in first.';
  if (e instanceof ApiError) {
    if (e.status === 503) return 'ElderGuard is paused right now. If a call feels wrong, hang up.';
    if (e.status === 429) return 'ElderGuard has reached today’s listening limit. If a call feels wrong, hang up.';
    if (e.status === 404) return 'This phone is not set up with ElderGuard yet.';
  }
  return 'ElderGuard could not start. If a call feels wrong, hang up.';
}

// Home: one primary action.
export default function Home() {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const checkThisCall = async () => {
    // One intent per tap: the backend allows five a minute and each expires after 60 s.
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      const intent = await createIntent();
      if (!isGuardianLineNumber(intent.guardian_line_number)) throw new Error('bad line number');
      router.push({ pathname: '/call/[sessionId]', params: { sessionId: intent.session_id } });
      await dialGuardianLine(intent.guardian_line_number);
    } catch (e) {
      setProblem(explain(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: EG_TOKENS.sand }}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 24, gap: 28, justifyContent: 'space-between' }}>
        <Wordmark />
        <View style={{ gap: 16, alignItems: 'center' }}>
          <Shield size={72} />
          <Headline style={{ textAlign: 'center' }}>On a call that feels wrong?</Headline>
          <Body style={{ textAlign: 'center' }}>Tap the big button. ElderGuard will join the call and listen with you.</Body>
        </View>
        <View style={{ gap: 14 }}>
          {problem && (
            <View accessibilityLiveRegion="polite">
              <Body style={{ color: EG_TOKENS.alert }}>{problem}</Body>
            </View>
          )}
          <PrimaryButton
            onPress={checkThisCall}
            disabled={busy}
            accessibilityHint="Calls the ElderGuard line so it can listen to this call"
          >
            {busy ? 'Starting…' : 'Check this call'}
          </PrimaryButton>
          <SecondaryButton accessibilityHint="Check a text, letter, or email you are unsure about">
            Show me something odd
          </SecondaryButton>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
