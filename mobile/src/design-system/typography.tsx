import type { ReactNode } from 'react';
import { Text, type StyleProp, type TextStyle } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

type Common = { children: ReactNode; style?: StyleProp<TextStyle> };

// The site's wordmark: Cormorant Garamond, brown.
export function Wordmark({ size = 26, color, style }: { size?: number; color?: string; style?: StyleProp<TextStyle> }) {
  return (
    <Text
      accessibilityRole="header"
      maxFontSizeMultiplier={1.4}
      style={[{ fontFamily: EG_FONTS.serif, fontSize: size, letterSpacing: 0.5, color: color ?? EG_TOKENS.brown }, style]}
    >
      ElderGuard
    </Text>
  );
}

export function Eyebrow({ children, color, style }: Common & { color?: string }) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.sansMedium,
          fontSize: 13,
          letterSpacing: 1.5,
          textTransform: 'uppercase',
          color: color ?? EG_TOKENS.textMid,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

// Cormorant has a small x-height, so headings run larger than the Fraunces sizes they replace.
export function Headline({ children, size = 38, style }: Common & { size?: number }) {
  return (
    <Text
      accessibilityRole="header"
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.serif,
          fontSize: size,
          lineHeight: Math.round(size * 1.2),
          letterSpacing: -0.5,
          color: EG_TOKENS.brown,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Subhead({ children, size = 26, style }: Common & { size?: number }) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        { fontFamily: EG_FONTS.serifSoft, fontSize: size, lineHeight: Math.round(size * 1.25), color: EG_TOKENS.burgundy },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Body({ children, size = 18, style }: Common & { size?: number }) {
  return (
    <Text
      maxFontSizeMultiplier={MAX_FONT_SCALE}
      style={[
        {
          fontFamily: EG_FONTS.sans,
          fontSize: size,
          lineHeight: Math.round(size * 1.6),
          color: EG_TOKENS.textMid,
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
      style={[{ fontFamily: EG_FONTS.serifItalic, fontSize: 22, color: EG_TOKENS.brown }, style]}
    >
      {children}
    </Text>
  );
}
