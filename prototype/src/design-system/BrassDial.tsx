import { EG_FONTS, EG_TOKENS, type Tone } from './tokens';
import { Eyebrow } from './typography';

type BrassDialProps = {
  value?: number;
  state?: Tone;
  size?: number;
  label?: string;
};

export function BrassDial({
  value = 0,
  state = 'ok',
  size = 200,
  label,
}: BrassDialProps) {
  const center = size / 2;
  const radius = size / 2 - 18;
  const startA = -210;
  const endA = 30;
  const sweep = endA - startA;
  const valA = startA + (value / 100) * sweep;

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

  const stateColor =
    state === 'alert'
      ? EG_TOKENS.alert
      : state === 'caution'
      ? EG_TOKENS.caution
      : EG_TOKENS.ok;

  const dashLen = (sweep / 360) * 2 * Math.PI * radius * (value / 100);

  const labelPt = (frac: number) => point(startA + sweep * frac, radius + 22);
  const [safeX, safeY] = labelPt(0.08);
  const [watchX, watchY] = labelPt(0.5);
  const [stopX, stopY] = labelPt(0.92);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg
        width={size}
        height={size * 0.78}
        viewBox={`0 0 ${size} ${size * 0.78}`}
        style={{ display: 'block' }}
      >
        <circle
          cx={center}
          cy={center}
          r={radius + 12}
          fill="none"
          stroke={EG_TOKENS.brass}
          strokeWidth="1.5"
          opacity="0.4"
        />
        <path d={arc} fill="none" stroke={EG_TOKENS.rule} strokeWidth="3" />
        <path
          d={arc}
          fill="none"
          stroke={stateColor}
          strokeWidth="3"
          strokeDasharray={`${dashLen} 1000`}
        />
        {ticks.map((t, i) => (
          <line
            key={i}
            x1={t.x1}
            y1={t.y1}
            x2={t.x2}
            y2={t.y2}
            stroke={EG_TOKENS.ink}
            strokeWidth={t.major ? 1.5 : 1}
            opacity={t.major ? 0.5 : 0.25}
          />
        ))}
        <text
          x={safeX}
          y={safeY}
          textAnchor="middle"
          fontSize="9"
          fontWeight="700"
          fill={EG_TOKENS.ok}
          style={{ fontFamily: EG_FONTS.sans, letterSpacing: '0.12em' }}
        >
          SAFE
        </text>
        <text
          x={watchX}
          y={watchY}
          textAnchor="middle"
          fontSize="9"
          fontWeight="700"
          fill={EG_TOKENS.caution}
          style={{ fontFamily: EG_FONTS.sans, letterSpacing: '0.12em' }}
        >
          WATCH
        </text>
        <text
          x={stopX}
          y={stopY}
          textAnchor="middle"
          fontSize="9"
          fontWeight="700"
          fill={EG_TOKENS.alert}
          style={{ fontFamily: EG_FONTS.sans, letterSpacing: '0.12em' }}
        >
          STOP
        </text>
        <line
          x1={center}
          y1={center}
          x2={nx}
          y2={ny}
          stroke={EG_TOKENS.ink}
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle
          cx={center}
          cy={center}
          r="6"
          fill={EG_TOKENS.brass}
          stroke={EG_TOKENS.ink}
          strokeWidth="1.5"
        />
      </svg>
      {label && <Eyebrow style={{ marginTop: 4 }}>{label}</Eyebrow>}
    </div>
  );
}
