import type { CSSProperties, ReactNode } from 'react';
import { EG_FONTS, EG_TOKENS } from './tokens';

type Common = { children: ReactNode; style?: CSSProperties };

export function Eyebrow({
  children,
  color,
  style,
}: Common & { color?: string }) {
  return (
    <div
      style={{
        fontFamily: EG_FONTS.sans,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: color ?? EG_TOKENS.inkMuted,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function Headline({
  children,
  size = 28,
  style,
}: Common & { size?: number }) {
  return (
    <h1
      style={{
        fontFamily: EG_FONTS.serif,
        fontSize: size,
        fontWeight: 500,
        lineHeight: 1.12,
        letterSpacing: '-0.018em',
        margin: 0,
        color: EG_TOKENS.ink,
        ...style,
      }}
    >
      {children}
    </h1>
  );
}

export function Body({
  children,
  size = 15,
  style,
}: Common & { size?: number }) {
  return (
    <p
      style={{
        fontFamily: EG_FONTS.sans,
        fontSize: size,
        fontWeight: 400,
        lineHeight: 1.5,
        margin: 0,
        color: EG_TOKENS.inkSoft,
        ...style,
      }}
    >
      {children}
    </p>
  );
}

export function Signature({ children, style }: Common) {
  return (
    <div
      style={{
        fontFamily: EG_FONTS.serif,
        fontStyle: 'italic',
        fontSize: 16,
        fontWeight: 400,
        color: EG_TOKENS.inkSoft,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
