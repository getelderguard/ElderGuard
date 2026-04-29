import type { CSSProperties, ReactNode } from 'react';
import { EG_FONTS, EG_TOKENS } from './tokens';

type LetterheadProps = {
  children: ReactNode;
  tape?: boolean;
  style?: CSSProperties;
};

export function Letterhead({ children, tape = true, style }: LetterheadProps) {
  return (
    <div
      style={{
        position: 'relative',
        background: EG_TOKENS.card,
        borderRadius: 4,
        padding: '24px 22px 22px',
        boxShadow:
          '0 1px 0 rgba(31,39,71,0.08), 0 14px 32px -18px rgba(31,39,71,0.22)',
        ...style,
      }}
    >
      {tape && (
        <span
          style={{
            position: 'absolute',
            top: -10,
            left: 28,
            width: 78,
            height: 18,
            background: 'rgba(200,155,91,0.55)',
            transform: 'rotate(-2deg)',
            borderRadius: 1,
            boxShadow: 'inset 0 0 0 1px rgba(200,155,91,0.3)',
          }}
        />
      )}
      {children}
    </div>
  );
}

export function FromLine({
  name = 'Jarmar',
  avatar = 'J',
}: {
  name?: string;
  avatar?: string;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: EG_TOKENS.ink,
          color: EG_TOKENS.paper,
          display: 'grid',
          placeItems: 'center',
          fontFamily: EG_FONTS.serif,
          fontSize: 15,
          fontWeight: 500,
        }}
      >
        {avatar}
      </div>
      <div>
        <div
          style={{
            fontSize: 11,
            color: EG_TOKENS.inkMuted,
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}
        >
          From
        </div>
        <div
          style={{
            fontFamily: EG_FONTS.serif,
            fontSize: 15,
            color: EG_TOKENS.ink,
          }}
        >
          {name}
        </div>
      </div>
    </div>
  );
}
