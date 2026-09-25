import type { CSSProperties, ReactNode } from 'react';
import { EG_FONTS, EG_TOKENS } from './tokens';

type PhoneProps = {
  children: ReactNode;
  statusDark?: boolean;
};

export function Phone({ children, statusDark = false }: PhoneProps) {
  return (
    <div style={phoneOuter}>
      <div style={phoneScreen}>
        <StatusBar dark={statusDark} />
        {children}
      </div>
    </div>
  );
}

const phoneOuter: CSSProperties = {
  width: 360,
  height: 720,
  borderRadius: 44,
  background: '#000',
  padding: 8,
  boxShadow:
    '0 20px 60px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.06)',
};

const phoneScreen: CSSProperties = {
  width: '100%',
  height: '100%',
  borderRadius: 36,
  overflow: 'hidden',
  position: 'relative',
  background: EG_TOKENS.paper,
  fontFamily: EG_FONTS.sans,
  color: EG_TOKENS.ink,
};

export function StatusBar({ dark = false }: { dark?: boolean }) {
  const c = dark ? '#fff' : EG_TOKENS.ink;
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 44,
        padding: '14px 28px 0',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 14,
        fontWeight: 600,
        color: c,
        zIndex: 50,
      }}
    >
      <span>9:41</span>
      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <span style={{ fontSize: 11 }}>●●●●</span>
        <span style={{ fontSize: 11 }}>WiFi</span>
        <span
          style={{
            display: 'inline-block',
            width: 22,
            height: 11,
            border: `1.5px solid ${c}`,
            borderRadius: 3,
            position: 'relative',
          }}
        >
          <span
            style={{
              position: 'absolute',
              inset: 1,
              background: c,
              borderRadius: 1,
            }}
          />
        </span>
      </span>
    </div>
  );
}
