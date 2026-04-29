import type { CSSProperties, ReactNode } from 'react';
import { EG_FONTS, EG_TOKENS } from './tokens';

type BtnProps = {
  children: ReactNode;
  onClick?: () => void;
  style?: CSSProperties;
};

export function PrimaryButton({
  children,
  onClick,
  danger,
  style,
}: BtnProps & { danger?: boolean }) {
  const bg = danger ? EG_TOKENS.alert : EG_TOKENS.ink;
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        padding: '18px 20px',
        background: bg,
        color: EG_TOKENS.paper,
        border: 'none',
        borderRadius: 14,
        fontFamily: EG_FONTS.sans,
        fontSize: 17,
        fontWeight: 600,
        letterSpacing: '-0.005em',
        cursor: 'pointer',
        ...style,
      }}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, style }: BtnProps) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        padding: '17px 20px',
        background: 'transparent',
        color: EG_TOKENS.ink,
        border: `1.5px solid ${EG_TOKENS.ink}`,
        borderRadius: 14,
        fontFamily: EG_FONTS.sans,
        fontSize: 16,
        fontWeight: 600,
        cursor: 'pointer',
        ...style,
      }}
    >
      {children}
    </button>
  );
}

export function GhostLink({ children, onClick, style }: BtnProps) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'none',
        border: 'none',
        fontFamily: EG_FONTS.sans,
        fontSize: 14,
        fontWeight: 600,
        color: EG_TOKENS.ink,
        opacity: 0.6,
        cursor: 'pointer',
        padding: 4,
        textDecoration: 'underline',
        textUnderlineOffset: 4,
        ...style,
      }}
    >
      {children}
    </button>
  );
}
