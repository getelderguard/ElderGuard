import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { useAuth } from '@/auth/AuthGate';
import { Body, EG_TOKENS, GhostLink, Headline, Page, PrimaryButton, TextField } from '@/design-system';

export default function AboutYou() {
  const { signOut } = useAuth();
  const [name, setName] = useState('');
  const [nickname, setNickname] = useState('');
  const [problem, setProblem] = useState<string | null>(null);

  const next = () => {
    const displayName = name.trim();
    if (!displayName) {
      setProblem('Please enter your first name.');
      return;
    }
    router.push({
      pathname: '/consent',
      params: { displayName: displayName.slice(0, 60), nickname: (nickname.trim() || 'Mom').slice(0, 30) },
    });
  };

  return (
    <Page
      actions={
        <>
          <PrimaryButton onPress={next}>Next</PrimaryButton>
          <GhostLink onPress={signOut}>Use a different phone number</GhostLink>
        </>
      }
    >
      <Headline>About you</Headline>
      <Body>Your family will see these names in ElderGuard.</Body>
      <TextField
        label="Your first name"
        value={name}
        onChangeText={setName}
        autoComplete="given-name"
        textContentType="givenName"
        autoCapitalize="words"
        maxLength={60}
        returnKeyType="next"
      />
      <TextField
        label="What does your family call you?"
        value={nickname}
        onChangeText={setNickname}
        placeholder="Mom, Grandma, Papa…"
        autoCapitalize="words"
        maxLength={30}
        returnKeyType="done"
        onSubmitEditing={next}
      />
      {problem && (
        <View accessibilityLiveRegion="polite">
          <Body style={{ color: EG_TOKENS.alert }}>{problem}</Body>
        </View>
      )}
    </Page>
  );
}
