import type { ReactNode } from 'react';
import {
  Body,
  BrassDial,
  EG_FONTS,
  EG_TOKENS,
  Eyebrow,
  FromLine,
  GhostLink,
  Headline,
  Letterhead,
  Phone,
  PrimaryButton,
  SecondaryButton,
} from '../design-system';
import type { Nav } from '../navigator/types';

type Tone = 'neutral' | 'caution' | 'alert';

function CallBar({
  name = '+1 (415) 555-0142',
  tone = 'neutral',
}: {
  name?: string;
  tone?: Tone;
}) {
  const bg =
    tone === 'alert'
      ? EG_TOKENS.alert
      : tone === 'caution'
      ? EG_TOKENS.caution
      : EG_TOKENS.ink;
  return (
    <div
      style={{
        background: bg,
        color: EG_TOKENS.paper,
        padding: '60px 22px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: 'rgba(245,237,224,0.18)',
          display: 'grid',
          placeItems: 'center',
          fontSize: 16,
        }}
      >
        📞
      </div>
      <div>
        <div
          style={{
            fontSize: 11,
            opacity: 0.7,
            fontWeight: 600,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          On a call · 2:14
        </div>
        <div style={{ fontFamily: EG_FONTS.serif, fontSize: 17 }}>{name}</div>
      </div>
    </div>
  );
}

function CallShell({
  tone,
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return (
    <Phone statusDark>
      <CallBar tone={tone} />
      <div
        style={{
          padding: '28px 24px',
          height: 'calc(100% - 130px)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {children}
      </div>
    </Phone>
  );
}

export function CallClear({ nav }: { nav: Nav }) {
  return (
    <CallShell tone="neutral">
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
        <BrassDial value={12} state="ok" label="Listening" />
      </div>
      <Letterhead style={{ marginTop: 22 }}>
        <FromLine />
        <Headline size={24} style={{ marginTop: 14 }}>
          Sounds fine so far.
        </Headline>
        <Body size={15} style={{ marginTop: 10 }}>
          I'm listening. If anything starts to feel off — money, urgency,
          secrets — I'll step in.
        </Body>
      </Letterhead>
      <div style={{ marginTop: 'auto', textAlign: 'center' }}>
        <GhostLink onClick={() => nav('call-caution')}>
          Hang up the call
        </GhostLink>
      </div>
    </CallShell>
  );
}

export function CallCaution({ nav }: { nav: Nav }) {
  return (
    <CallShell tone="caution">
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
        <BrassDial value={58} state="caution" label="Watching closely" />
      </div>
      <Letterhead style={{ marginTop: 22 }}>
        <FromLine />
        <Headline size={22} style={{ marginTop: 14 }}>
          Something's a little off.
        </Headline>
        <Body size={15} style={{ marginTop: 10 }}>
          They mentioned{' '}
          <em
            style={{
              background: EG_TOKENS.cautionSoft,
              padding: '1px 4px',
              fontStyle: 'normal',
            }}
          >
            gift cards
          </em>
          . Keep listening — I'll only break in if it gets worse.
        </Body>
      </Letterhead>
      <div style={{ marginTop: 14 }}>
        <SecondaryButton onClick={() => nav('call-checking')}>
          Step in now
        </SecondaryButton>
      </div>
      <div style={{ marginTop: 'auto', textAlign: 'center' }}>
        <GhostLink onClick={() => nav('call-falseAlarm')}>
          Hang up the call
        </GhostLink>
      </div>
    </CallShell>
  );
}

export function CallChecking({ nav }: { nav: Nav }) {
  return (
    <CallShell tone="alert">
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
        <BrassDial value={86} state="alert" label="Checking with Jarmar" />
      </div>
      <Letterhead style={{ marginTop: 22 }}>
        <FromLine />
        <Headline size={22} style={{ marginTop: 14 }}>
          Hold on a moment, Mom.
        </Headline>
        <Body size={15} style={{ marginTop: 10 }}>
          I'm pinging Jarmar to take a look. About 5 seconds.
        </Body>
        <div
          style={{
            marginTop: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div
            style={{
              flex: 1,
              height: 6,
              background: EG_TOKENS.alertWash,
              borderRadius: 3,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: '60%',
                height: '100%',
                background: EG_TOKENS.alert,
              }}
            />
          </div>
          <span
            style={{
              fontFamily: EG_FONTS.serif,
              fontSize: 14,
              color: EG_TOKENS.alert,
              fontWeight: 600,
            }}
          >
            3s
          </span>
        </div>
      </Letterhead>
      <div style={{ marginTop: 14 }}>
        <SecondaryButton onClick={() => nav('call-clear')}>
          It's fine — cancel
        </SecondaryButton>
      </div>
      <div style={{ marginTop: 'auto', textAlign: 'center' }}>
        <GhostLink onClick={() => nav('call-takeover')}>
          Continue to takeover →
        </GhostLink>
      </div>
    </CallShell>
  );
}

export function CallTakeover({ nav }: { nav: Nav }) {
  return (
    <CallShell tone="alert">
      <div
        style={{
          background: EG_TOKENS.alertWash,
          borderRadius: 14,
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            background: EG_TOKENS.alert,
            color: EG_TOKENS.paper,
            display: 'grid',
            placeItems: 'center',
            fontSize: 16,
          }}
        >
          ●
        </div>
        <div>
          <Eyebrow style={{ color: EG_TOKENS.alert }}>
            Speaking now · in your voice
          </Eyebrow>
          <div style={{ fontSize: 13, color: EG_TOKENS.ink, marginTop: 2 }}>
            Mom, you can put the phone down.
          </div>
        </div>
      </div>
      <Letterhead>
        <FromLine />
        <Headline size={22} style={{ marginTop: 14 }}>
          I've got it from here.
        </Headline>
        <div
          style={{
            marginTop: 12,
            fontFamily: EG_FONTS.serif,
            fontSize: 18,
            lineHeight: 1.45,
            color: EG_TOKENS.ink,
            padding: 12,
            background: EG_TOKENS.paper,
            borderRadius: 8,
          }}
        >
          "My son helps me with calls. We're not interested. Don't call back."
        </div>
        <div
          style={{
            marginTop: 14,
            display: 'flex',
            gap: 3,
            alignItems: 'center',
            height: 28,
          }}
        >
          {[12, 18, 8, 22, 14, 26, 10, 20, 16, 24, 8, 18, 12, 22, 14, 10, 20, 16, 24, 12, 18, 8, 22, 14].map(
            (h, i) => (
              <div
                key={i}
                style={{
                  width: 3,
                  height: h,
                  background: EG_TOKENS.alert,
                  borderRadius: 2,
                  opacity: i < 14 ? 1 : 0.3,
                }}
              />
            )
          )}
        </div>
      </Letterhead>
      <div style={{ marginTop: 'auto' }}>
        <PrimaryButton danger onClick={() => nav('call-falseAlarm')}>
          Hang up
        </PrimaryButton>
      </div>
    </CallShell>
  );
}

export function CallTakeoverNoVoice({ nav }: { nav: Nav }) {
  return (
    <CallShell tone="alert">
      <div
        style={{
          background: EG_TOKENS.alertWash,
          borderRadius: 14,
          padding: '14px 16px',
          marginBottom: 16,
        }}
      >
        <Eyebrow style={{ color: EG_TOKENS.alert }}>
          Read this out loud, Mom
        </Eyebrow>
        <div style={{ fontSize: 12, color: EG_TOKENS.inkSoft, marginTop: 4 }}>
          (We didn't record Jarmar's voice — that's fine.)
        </div>
      </div>
      <Letterhead>
        <Headline size={26} style={{ lineHeight: 1.2 }}>
          "My son helps me with calls. We're not interested. Don't call back."
        </Headline>
        <Body size={14} style={{ marginTop: 14 }}>
          Then hang up. You don't owe them anything else.
        </Body>
      </Letterhead>
      <div style={{ marginTop: 'auto' }}>
        <PrimaryButton danger onClick={() => nav('call-falseAlarm')}>
          Hang up
        </PrimaryButton>
      </div>
    </CallShell>
  );
}

export function CallFalseAlarm({ nav }: { nav: Nav }) {
  return (
    <Phone>
      <div
        style={{
          padding: '64px 24px 28px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Eyebrow style={{ color: EG_TOKENS.brass }}>One more thing</Eyebrow>
        <Letterhead style={{ marginTop: 16 }}>
          <FromLine />
          <Headline size={24} style={{ marginTop: 14 }}>
            Was that a false alarm?
          </Headline>
          <Body size={15} style={{ marginTop: 10 }}>
            Tell Jarmar so he doesn't worry — and so I learn to be less jumpy
            next time.
          </Body>
        </Letterhead>
        <div
          style={{
            marginTop: 22,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <PrimaryButton onClick={() => nav('home')}>
            Yes — false alarm
          </PrimaryButton>
          <SecondaryButton onClick={() => nav('home')}>
            No — it really was a scammer
          </SecondaryButton>
        </div>
        <div style={{ marginTop: 'auto', textAlign: 'center' }}>
          <GhostLink onClick={() => nav('home')}>
            Skip — don't tell Jarmar
          </GhostLink>
        </div>
      </div>
    </Phone>
  );
}
