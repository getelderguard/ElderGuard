import { ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Body, EG_TOKENS, Eyebrow, Headline, PrimaryButton, SecondaryButton } from '@/design-system';

// Home: one primary action. The buttons are wired to the session flow in the next slice.
export default function Home() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: EG_TOKENS.paper }}>
      <ScrollView contentContainerStyle={{ flexGrow: 1, padding: 24, gap: 28, justifyContent: 'space-between' }}>
        <View style={{ gap: 12, paddingTop: 24 }}>
          <Eyebrow>ElderGuard</Eyebrow>
          <Headline>On a call that feels wrong?</Headline>
          <Body>Tap the big button. ElderGuard will join the call and listen with you.</Body>
        </View>
        <View style={{ gap: 14 }}>
          <PrimaryButton accessibilityHint="Calls the ElderGuard line so it can listen to this call">
            Check this call
          </PrimaryButton>
          <SecondaryButton accessibilityHint="Check a text, letter, or email you are unsure about">
            Show me something odd
          </SecondaryButton>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
