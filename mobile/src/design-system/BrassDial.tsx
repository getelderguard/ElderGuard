import { View } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText } from 'react-native-svg';

import type { Tier } from '@/session/tiers';

import { EG_FONTS, EG_TOKENS } from './tokens';
import { Eyebrow } from './typography';

type BrassDialProps = {
  value?: number;
  tier?: Tier;
  size?: number;
  label?: string;
};

// Listening is neutral brass, never green: the dial must not read as "safe" while a call is live.
const TIER_COLOR: Record<Tier, string> = {
  listening: EG_TOKENS.brass,
  caution: EG_TOKENS.caution,
  stop: EG_TOKENS.alert,
  unknown: EG_TOKENS.faint,
  no_audio: EG_TOKENS.faint,
};

const TIER_SPOKEN: Record<Tier, string> = {
  listening: 'Listening',
  caution: 'Caution',
  stop: 'Stop',
  unknown: 'Not sure right now',
  no_audio: 'Cannot hear the call',
};

// Geometry is unchanged from prototype/src/design-system/BrassDial.tsx.
export function BrassDial({ value = 0, tier = 'listening', size = 200, label }: BrassDialProps) {
  const v = Math.max(0, Math.min(100, value));
  const center = size / 2;
  const radius = size / 2 - 18;
  const startA = -210;
  const endA = 30;
  const sweep = endA - startA;
  const valA = startA + (v / 100) * sweep;

  const point = (a: number, r: number): [number, number] => {
    const rad = (a * Math.PI) / 180;
    return [center + r * Math.cos(rad), center + r * Math.sin(rad)];
  };

  const [sx, sy] = point(startA, radius);
  const [ex, ey] = point(endA, radius);
  const arc = `M ${sx} ${sy} A ${radius} ${radius} 0 1 1 ${ex} ${ey}`;

  const ticks: { x1: number; y1: number; x2: number; y2: number; major: boolean }[] = [];
  for (let i = 0; i <= 10; i++) {
    const a = startA + (sweep * i) / 10;
    const [x1, y1] = point(a, radius - 4);
    const [x2, y2] = point(a, radius + (i % 5 === 0 ? 8 : 4));
    ticks.push({ x1, y1, x2, y2, major: i % 5 === 0 });
  }
  const [nx, ny] = point(valA, radius - 14);

  const stateColor = TIER_COLOR[tier];
  const dashLen = (sweep / 360) * 2 * Math.PI * radius * (v / 100);

  const labelPt = (frac: number) => point(startA + sweep * frac, radius + 22);
  const scale: [number, string, string][] = [
    [0.08, 'LISTEN', EG_TOKENS.textMid],
    [0.5, 'CAUTION', EG_TOKENS.caution],
    [0.92, 'STOP', EG_TOKENS.alert],
  ];

  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={`${TIER_SPOKEN[tier]}. Scam meter at ${Math.round(v)} out of 100.`}
      style={{ alignItems: 'center' }}
    >
      <Svg width={size} height={size * 0.78} viewBox={`0 0 ${size} ${size * 0.78}`}>
        <Circle cx={center} cy={center} r={radius + 12} fill="none" stroke={EG_TOKENS.turquoise} strokeWidth={1.5} opacity={0.4} />
        <Path d={arc} fill="none" stroke={EG_TOKENS.rule} strokeWidth={3} />
        <Path d={arc} fill="none" stroke={stateColor} strokeWidth={3} strokeDasharray={`${dashLen} 1000`} />
        {ticks.map((t, i) => (
          <Line
            key={i}
            x1={t.x1}
            y1={t.y1}
            x2={t.x2}
            y2={t.y2}
            stroke={EG_TOKENS.brown}
            strokeWidth={t.major ? 1.5 : 1}
            opacity={t.major ? 0.5 : 0.25}
          />
        ))}
        {scale.map(([frac, text, color]) => {
          const [x, y] = labelPt(frac);
          return (
            <SvgText
              key={text}
              x={x}
              y={y}
              textAnchor="middle"
              fontSize={9}
              fontFamily={EG_FONTS.sansSemi}
              letterSpacing={1}
              fill={color}
            >
              {text}
            </SvgText>
          );
        })}
        <Line x1={center} y1={center} x2={nx} y2={ny} stroke={EG_TOKENS.brown} strokeWidth={3} strokeLinecap="round" />
        <Circle cx={center} cy={center} r={6} fill={EG_TOKENS.brass} stroke={EG_TOKENS.brown} strokeWidth={1.5} />
      </Svg>
      {label && <Eyebrow style={{ marginTop: 4 }}>{label}</Eyebrow>}
    </View>
  );
}
