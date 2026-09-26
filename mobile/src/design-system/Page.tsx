import type { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EG_TOKENS } from './tokens';

// A full screen: content at the top, actions at the bottom, keyboard never covers the button.
export function Page({ children, actions, background }: { children: ReactNode; actions?: ReactNode; background?: string }) {
  const bg = background ?? EG_TOKENS.sand;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ flexGrow: 1, padding: 24, gap: 28, justifyContent: 'space-between' }}
        >
          <View style={{ gap: 16 }}>{children}</View>
          {actions && <View style={{ gap: 14 }}>{actions}</View>}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
