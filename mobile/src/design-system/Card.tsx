import type { ReactNode } from 'react';
import { Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

// The site's .card: white, hairline brown border, 4 pt corners.
export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return (
    <View
      style={[
        {
          backgroundColor: EG_TOKENS.white,
          borderRadius: 4,
          borderWidth: 1,
          borderColor: EG_TOKENS.border,
          paddingTop: 28,
          paddingHorizontal: 22,
          paddingBottom: 22,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

// Name and initial come from the account; no defaults, so a missing name is visible in review.
export function FromLine({ name, avatar }: { name: string; avatar: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }} accessible accessibilityLabel={`From ${name}`}>
      <View
        style={{
          width: 40,
          height: 40,
          borderRadius: 20,
          borderWidth: 1.5,
          borderColor: EG_TOKENS.turquoise,
          backgroundColor: EG_TOKENS.white,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text maxFontSizeMultiplier={1.2} style={{ fontFamily: EG_FONTS.serif, fontSize: 20, color: EG_TOKENS.turquoiseDark }}>
          {avatar}
        </Text>
      </View>
      <View>
        <Text
          maxFontSizeMultiplier={MAX_FONT_SCALE}
          style={{ fontFamily: EG_FONTS.sansMedium, fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase', color: EG_TOKENS.textLight }}
        >
          From
        </Text>
        <Text maxFontSizeMultiplier={MAX_FONT_SCALE} style={{ fontFamily: EG_FONTS.serif, fontSize: 20, color: EG_TOKENS.brown }}>
          {name}
        </Text>
      </View>
    </View>
  );
}
