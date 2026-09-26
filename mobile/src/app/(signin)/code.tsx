import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { confirmCode, explainAuthError, pendingPhone } from '@/auth/firebase';
import { Body, EG_TOKENS, GhostLink, Headline, Page, PrimaryButton, TextField } from '@/design-system';

function pretty(e164: string | null) {
  if (!e164) return 'your phone';
  const d = e164.slice(2);
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

// On success Firebase reports the new user and the root layout moves on to setup by itself.
export default function CodeScreen() {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const confirm = async (value = code) => {
    if (busy) return;
    if (!/^\d{6}$/.test(value)) {
      setProblem('The code is 6 digits.');
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      await confirmCode(value);
    } catch (e) {
      setProblem(explainAuthError(e));
      setBusy(false);
    }
  };

  const onChange = (text: string) => {
    const digits = text.replace(/\D/g, '').slice(0, 6);
    setCode(digits);
    if (digits.length === 6) confirm(digits);
  };

  return (
    <Page
      actions={
        <>
          <PrimaryButton onPress={() => confirm()} disabled={busy}>
            {busy ? 'Checking…' : 'Continue'}
          </PrimaryButton>
          <GhostLink onPress={() => router.back()}>Send a new code</GhostLink>
        </>
      }
    >
      <Headline>Enter the code</Headline>
      <Body>We texted a 6-digit code to {pretty(pendingPhone())}.</Body>
      <TextField
        label="Code"
        value={code}
        onChangeText={onChange}
        keyboardType="number-pad"
        autoComplete="sms-otp"
        textContentType="oneTimeCode"
        maxLength={6}
        autoFocus
        style={{ letterSpacing: 8 }}
      />
      {problem && (
        <View accessibilityLiveRegion="polite">
          <Body style={{ color: EG_TOKENS.alert }}>{problem}</Body>
        </View>
      )}
    </Page>
  );
}
