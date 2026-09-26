// Palette and type match getelderguard.org (styles.css :root) so the app and site read as one brand.
export const EG_TOKENS = {
  // Site palette, verbatim
  sand:          '#F5EDE0',
  cream:         '#EDE0CE',
  creamLight:    '#FAF5EC',
  turquoise:     '#3D8B8B',
  turquoiseDark: '#2F7A7A',
  burgundy:      '#6B2D2D',
  brown:         '#5C4033',
  brownLight:    '#7A5C42',
  deepRed:       '#9C3D3D',
  textDark:      '#3A2D24',
  textMid:       '#6B5D4F',
  textLight:     '#9A8B7C',
  white:         '#FFFFFF',
  border:        'rgba(92,64,51,0.12)',

  // Live-call tier colors. Listening is brass, never green or turquoise-as-"all clear":
  // the dial must not read as "safe" while a call is live.
  brass:         '#B8894A',
  caution:       '#A8761F',
  cautionWash:   '#F6E7C8',
  alert:         '#9C3D3D',
  alertWash:     '#F7E3DC',
  faint:         'rgba(58,45,36,0.30)',
  rule:          'rgba(58,45,36,0.14)',
} as const;

// React Native ignores fontWeight on custom families, so each weight is its own family.
// Names match the keys loaded in src/app/_layout.tsx.
export const EG_FONTS = {
  serif:     'CormorantGaramond_600SemiBold',
  serifSoft: 'CormorantGaramond_500Medium',
  serifItalic: 'CormorantGaramond_500Medium_Italic',
  sans:      'Inter_400Regular',
  sansMedium: 'Inter_500Medium',
  sansSemi:  'Inter_600SemiBold',
} as const;

// Seniors often run large text. Allow it, but cap it so layouts do not break.
export const MAX_FONT_SCALE = 1.8;
