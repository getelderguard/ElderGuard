import type { ReactNode } from 'react';
import { Text, type StyleProp, type TextStyle } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

type Common = { children: ReactNode; style?: StyleProp<TextStyle> };

export function Eyebrow({ children, color, style }: Common & { color?: string }) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.sansBold,
          fontSize: 12,
          letterSpacing: 2,
          textTransform: 'uppercase',
          color: color ?? EG_TOKENS.inkMuted,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Headline({ children, size = 30, style }: Common & { size?: number }) {
  return (
    <Text
      accessibilityRole="header"
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.serif,
          fontSize: size,
          lineHeight: Math.round(size * 1.15),
          letterSpacing: -0.5,
          color: EG_TOKENS.ink,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Body({ children, size = 17, style }: Common & { size?: number }) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.sans,
          fontSize: size,
          lineHeight: Math.round(size * 1.5),
          color: EG_TOKENS.inkSoft,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Signature({ children, style }: Common) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[{ fontFamily: EG_FONTS.serifItalic, fontSize: 18, color: EG_TOKENS.inkSoft }, style]}
    >
      {children}
    </Text>
  );
}
