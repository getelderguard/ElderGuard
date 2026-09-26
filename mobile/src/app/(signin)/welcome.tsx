import { router } from 'expo-router';
import { View } from 'react-native';

import { Body, Headline, Page, PrimaryButton, Shield, Wordmark } from '@/design-system';

export default function Welcome() {
  return (
    <Page actions={<PrimaryButton onPress={() => router.push('/phone')}>Get started</PrimaryButton>}>
      <Wordmark />
      <View style={{ alignItems: 'center', gap: 16, marginTop: 24 }}>
        <Shield size={80} />
        <Headline style={{ textAlign: 'center' }}>A second pair of ears on every call</Headline>
        <Body style={{ textAlign: 'center' }}>
          When a call feels wrong, ElderGuard listens with you and tells you if it sounds like a scam.
        </Body>
        <Body style={{ textAlign: 'center' }}>First, let’s make sure this is your phone.</Body>
      </View>
    </Page>
  );
}
