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

export const EG_FONTS = {
  serif: "'Fraunces', Georgia, serif",
  sans:  "'Public Sans', -apple-system, BlinkMacSystemFont, sans-serif",
  mono:  "'JetBrains Mono', 'Courier New', monospace",
} as const;

export type Tone = 'ok' | 'caution' | 'alert';
