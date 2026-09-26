import Svg, { Circle, Path } from 'react-native-svg';

import { EG_TOKENS } from './tokens';

// The shield from the site's hero, same paths and viewBox.
export function Shield({ size = 64, color = EG_TOKENS.turquoise }: { size?: number; color?: string }) {
  return (
    <Svg
      width={size}
      height={(size * 140) / 120}
      viewBox="0 0 120 140"
      fill="none"
      stroke={color}
      strokeWidth={2}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      <Path d="M60 4 L108 22 V68 C108 100 86 124 60 136 C34 124 12 100 12 68 V22 Z" />
      <Path d="M60 22 L92 34 V66 C92 88 78 106 60 116 C42 106 28 88 28 66 V34 Z" opacity={0.5} />
      <Circle cx={60} cy={68} r={14} opacity={0.6} />
    </Svg>
  );
}
