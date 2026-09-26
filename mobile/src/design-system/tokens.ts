// Colors carry over verbatim from prototype/src/design-system/tokens.ts.
export const EG_TOKENS = {
  paper:       '#f5ede0',
  paperDeep:   '#ecdfca',
  card:        '#ffffff',
  ink:         '#1f2747',
  inkSoft:     'rgba(31,39,71,0.72)',
  inkMuted:    'rgba(31,39,71,0.55)',
  inkFaint:    'rgba(31,39,71,0.32)',
  rule:        'rgba(31,39,71,0.14)',
  brass:       '#c89b5b',
  brassSoft:   '#e0c89a',
  alert:       '#c4533b',
  alertSoft:   '#f7d7cd',
  alertWash:   '#fbeae3',
  caution:     '#b58a2d',
  cautionSoft: '#f5e6c0',
  ok:          '#3f7d5b',
  okSoft:      '#cfe3d6',
} as const;

// React Native ignores fontWeight on custom families, so each weight is its own family.
// Names match the keys loaded in src/app/_layout.tsx.
export const EG_FONTS = {
  serif:       'Fraunces_500Medium',
  serifItalic: 'Fraunces_400Regular_Italic',
  sans:        'PublicSans_400Regular',
  sansSemi:    'PublicSans_600SemiBold',
  sansBold:    'PublicSans_700Bold',
} as const;

// Seniors often run large text. Allow it, but cap it so layouts do not break.
export const MAX_FONT_SCALE = 1.8;
