import type { ReactNode } from 'react';
import { Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

type LetterheadProps = {
  children: ReactNode;
  tape?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Letterhead({ children, tape = true, style }: LetterheadProps) {
  return (
    <View
      style={[
        {
          backgroundColor: EG_TOKENS.card,
          borderRadius: 4,
          paddingTop: 24,
          paddingHorizontal: 22,
          paddingBottom: 22,
          boxShadow: '0 1px 0 rgba(31,39,71,0.08), 0 14px 32px -18px rgba(31,39,71,0.22)',
        },
        style,
      ]}
    >
      {tape && (
        <View
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          style={{
            position: 'absolute',
            top: -10,
            left: 28,
            width: 78,
            height: 18,
            borderRadius: 1,
            backgroundColor: 'rgba(200,155,91,0.55)',
            transform: [{ rotate: '-2deg' }],
          }}
        />
      )}
      {children}
    </View>
  );
}

// Name and initial come from the account; no defaults, so a missing name is visible in review.
export function FromLine({ name, avatar }: { name: string; avatar: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }} accessible accessibilityLabel={`From ${name}`}>
      <View
        style={{
          width: 36,
          height: 36,
          borderRadius: 18,
          backgroundColor: EG_TOKENS.ink,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text maxFontSizeMultiplier={1.2} style={{ fontFamily: EG_FONTS.serif, fontSize: 16, color: EG_TOKENS.paper }}>
          {avatar}
        </Text>
      </View>
      <View>
        <Text
          maxFontSizeMultiplier={MAX_FONT_SCALE}
          style={{ fontFamily: EG_FONTS.sansSemi, fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase', color: EG_TOKENS.inkMuted }}
        >
          From
        </Text>
        <Text maxFontSizeMultiplier={MAX_FONT_SCALE} style={{ fontFamily: EG_FONTS.serif, fontSize: 17, color: EG_TOKENS.ink }}>
          {name}
        </Text>
      </View>
    </View>
  );
}
