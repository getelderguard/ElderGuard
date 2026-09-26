import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { explainAuthError, sendCode, toUsE164 } from '@/auth/firebase';
import { Body, EG_TOKENS, GhostLink, Headline, Page, PrimaryButton, TextField } from '@/design-system';

export default function PhoneScreen() {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const send = async () => {
    if (busy) return;
    const phone = toUsE164(value);
    if (!phone) {
      setProblem('Please enter a 10-digit US phone number.');
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      await sendCode(phone);
      router.push('/code');
    } catch (e) {
      setProblem(explainAuthError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      actions={
        <>
          <PrimaryButton onPress={send} disabled={busy}>
            {busy ? 'Sending…' : 'Text me a code'}
          </PrimaryButton>
          <GhostLink onPress={() => router.back()}>Back</GhostLink>
        </>
      }
    >
      <Headline>Your phone number</Headline>
      <Body>We will text you a 6-digit code to make sure this phone is yours.</Body>
      <TextField
        label="Phone number"
        value={value}
        onChangeText={setValue}
        placeholder="(555) 123-4567"
        keyboardType="phone-pad"
        autoComplete="tel"
        textContentType="telephoneNumber"
        returnKeyType="done"
        onSubmitEditing={send}
        autoFocus
      />
      {problem && (
        <View accessibilityLiveRegion="polite">
          <Body style={{ color: EG_TOKENS.alert }}>{problem}</Body>
        </View>
      )}
      <Body style={{ fontSize: 15 }}>
        ElderGuard keeps only the last four digits in plain view. Message and data rates may apply.
      </Body>
    </Page>
  );
}
