import { Text, TextInput, View, type TextInputProps } from 'react-native';

import { EG_FONTS, EG_TOKENS, MAX_FONT_SCALE } from './tokens';

// Large, labelled input. The label is visible text, not a placeholder, so it never disappears.
export function TextField({ label, ...input }: TextInputProps & { label: string }) {
  return (
    <View style={{ gap: 8 }}>
      <Text
        maxFontSizeMultiplier={MAX_FONT_SCALE}
        style={{ fontFamily: EG_FONTS.sansSemi, fontSize: 17, color: EG_TOKENS.textDark }}
      >
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        maxFontSizeMultiplier={MAX_FONT_SCALE}
        placeholderTextColor={EG_TOKENS.textLight}
        {...input}
        style={[
          {
            minHeight: 60,
            paddingHorizontal: 16,
            borderRadius: 12,
            borderWidth: 1.5,
            borderColor: EG_TOKENS.brownLight,
            backgroundColor: EG_TOKENS.white,
            fontFamily: EG_FONTS.sans,
            fontSize: 22,
            color: EG_TOKENS.textDark,
          },
          input.style,
        ]}
      />
    </View>
  );
}
