import * as Haptics from 'expo-haptics';
import type { ReactNode } from 'react';
import { Pressable, Text, type StyleProp, type ViewStyle } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

type BtnProps = {
  children: ReactNode;
  onPress?: () => void;
  disabled?: boolean;
  accessibilityHint?: string;
  style?: StyleProp<ViewStyle>;
};

// Every button is at least 60 pt tall and gives a light tap on press.
function press(onPress?: () => void) {
  return () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    onPress?.();
  };
}

export function PrimaryButton({
  children,
  onPress,
  danger,
  disabled,
  accessibilityHint,
  style,
}: BtnProps & { danger?: boolean }) {
  const bg = danger ? EG_TOKENS.alert : EG_TOKENS.turquoiseDark;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!disabled }}
      disabled={disabled}
      onPress={press(onPress)}
      style={({ pressed }) => [
        {
          minHeight: 60,
          paddingVertical: 18,
          paddingHorizontal: 20,
          borderRadius: 12,
          backgroundColor: bg,
          alignItems: 'center',
          justifyContent: 'center',
          opacity: disabled ? 0.6 : pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      <Text
        maxFontSizeMultiplier={MAX_FONT_SCALE}
        style={{ fontFamily: EG_FONTS.sansSemi, fontSize: 19, color: EG_TOKENS.white, textAlign: 'center' }}
      >
        {children}
      </Text>
    </Pressable>
  );
}

export function SecondaryButton({ children, onPress, disabled, accessibilityHint, style }: BtnProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: !!disabled }}
      disabled={disabled}
      onPress={press(onPress)}
      style={({ pressed }) => [
        {
          minHeight: 60,
          paddingVertical: 17,
          paddingHorizontal: 20,
          borderRadius: 12,
          borderWidth: 1.5,
          borderColor: EG_TOKENS.turquoise,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: pressed ? EG_TOKENS.cream : EG_TOKENS.white,
        },
        style,
      ]}
    >
      <Text
        maxFontSizeMultiplier={MAX_FONT_SCALE}
        style={{ fontFamily: EG_FONTS.sansSemi, fontSize: 18, color: EG_TOKENS.turquoiseDark, textAlign: 'center' }}
      >
        {children}
      </Text>
    </Pressable>
  );
}

export function GhostLink({ children, onPress, accessibilityHint, style }: BtnProps) {
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityHint={accessibilityHint}
      onPress={press(onPress)}
      hitSlop={12}
      style={[{ minHeight: 44, justifyContent: 'center', padding: 4 }, style]}
    >
      <Text
        maxFontSizeMultiplier={MAX_FONT_SCALE}
        style={{
          fontFamily: EG_FONTS.sansSemi,
          fontSize: 16,
          color: EG_TOKENS.textMid,
          textDecorationLine: 'underline',
        }}
      >
        {children}
      </Text>
    </Pressable>
  );
}
