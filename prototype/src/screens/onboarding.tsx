import type { ReactNode } from 'react';
import {
  Body,
  EG_FONTS,
  EG_TOKENS,
  Eyebrow,
  GhostLink,
  Headline,
  Letterhead,
  Phone,
  PrimaryButton,
  Signature,
} from '../design-system';
import type { Nav } from '../navigator/types';

export function OBSplash({ nav }: { nav: Nav }) {
  return (
    <Phone>
      <div style={page}>
        <Eyebrow style={{ color: EG_TOKENS.brass }}>ElderGuard</Eyebrow>
        <div style={{ marginTop: 80, textAlign: 'left' }}>
          <Headline size={42} style={{ marginBottom: 18 }}>
            Hi Jarmar —<br />
            let's set this up<br />
            on Mom's phone.
          </Headline>
          <Body size={16}>
            About 4 minutes. You'll teach the app what to listen for, and what
            to say if a scammer calls.
          </Body>
        </div>
        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <PrimaryButton onClick={() => nav('ob-1')}>Begin</PrimaryButton>
          <div style={{ textAlign: 'center' }}>
            <GhostLink>I'm not Jarmar</GhostLink>
          </div>
        </div>
      </div>
    </Phone>
  );
}

type StepProps = {
  n: 1 | 2 | 3 | 4;
  title: string;
  body: ReactNode;
  children: ReactNode;
  primary?: string;
  secondary?: string;
  onNext: () => void;
};

function OBStep({ n, title, body, children, primary = 'Next', secondary, onNext }: StepProps) {
  return (
    <Phone>
      <div style={page}>
        <Eyebrow style={{ color: EG_TOKENS.brass }}>Step {n} of 4</Eyebrow>
        <Headline size={28} style={{ marginTop: 14 }}>{title}</Headline>
        <Body size={15} style={{ marginTop: 12 }}>{body}</Body>
        <div style={{ marginTop: 22, flex: 1 }}>{children}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <PrimaryButton onClick={onNext}>{primary}</PrimaryButton>
          {secondary && (
            <div style={{ textAlign: 'center' }}>
              <GhostLink>{secondary}</GhostLink>
            </div>
          )}
        </div>
      </div>
    </Phone>
  );
}

export function OB1Relationship({ nav }: { nav: Nav }) {
  const roles = ['Son', 'Daughter', 'Grandchild', 'Other'];
  return (
    <OBStep
      n={1}
      title="Who are you setting this up for?"
      body="So I can address her by name and frame everything around your relationship."
      onNext={() => nav('ob-2')}
    >
      <Letterhead tape={false}>
        <Eyebrow>Their name</Eyebrow>
        <div style={fieldText}>Eleanor</div>
        <Eyebrow style={{ marginTop: 22 }}>What you call them</Eyebrow>
        <div style={fieldText}>Mom</div>
        <Eyebrow style={{ marginTop: 22 }}>You are</Eyebrow>
        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {roles.map((r, i) => {
            const active = i === 0;
            return (
              <div
                key={r}
                style={{
                  padding: '8px 14px',
                  borderRadius: 999,
                  border: `1.5px solid ${active ? EG_TOKENS.ink : EG_TOKENS.rule}`,
                  background: active ? EG_TOKENS.ink : 'transparent',
                  color: active ? EG_TOKENS.paper : EG_TOKENS.inkSoft,
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                {r}
              </div>
            );
          })}
        </div>
      </Letterhead>
    </OBStep>
  );
}

export function OB2Vulnerabilities({ nav }: { nav: Nav }) {
  const items: { l: string; on: boolean }[] = [
    { l: 'IRS / tax threats', on: true },
    { l: 'Medicare / insurance', on: true },
    { l: 'Tech support ("your computer is infected")', on: true },
    { l: 'Romance / friendship scams', on: false },
    { l: '"Grandchild in trouble"', on: true },
    { l: 'Charity / donation pressure', on: false },
  ];
  return (
    <OBStep
      n={2}
      title="What should I listen for?"
      body="Pick the calls Mom is most likely to get. We'll prioritize these — but I listen for everything."
      secondary="Not sure — pick common ones for me"
      onNext={() => nav('ob-3')}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((it, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '14px 16px',
              background: it.on ? EG_TOKENS.card : 'transparent',
              border: `1.5px solid ${it.on ? EG_TOKENS.ink : EG_TOKENS.rule}`,
              borderRadius: 12,
            }}
          >
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: 6,
                background: it.on ? EG_TOKENS.ink : 'transparent',
                border: `1.5px solid ${it.on ? EG_TOKENS.ink : EG_TOKENS.inkFaint}`,
                display: 'grid',
                placeItems: 'center',
                color: EG_TOKENS.paper,
                fontSize: 13,
                fontWeight: 700,
              }}
            >
              {it.on ? '✓' : ''}
            </div>
            <div
              style={{
                fontSize: 15,
                color: EG_TOKENS.ink,
                fontWeight: it.on ? 500 : 400,
              }}
            >
              {it.l}
            </div>
          </div>
        ))}
      </div>
    </OBStep>
  );
}

export function OB3VoiceScript({ nav }: { nav: Nav }) {
  return (
    <OBStep
      n={3}
      title="Record your voice for the takeover."
      body="If a scammer keeps pushing, I'll play this in your voice. About 8 seconds."
      primary="Tap to record"
      secondary="Skip — use a written script instead"
      onNext={() => nav('ob-4')}
    >
      <Letterhead>
        <Eyebrow>The script</Eyebrow>
        <div
          style={{
            marginTop: 12,
            fontFamily: EG_FONTS.serif,
            fontSize: 19,
            lineHeight: 1.45,
            color: EG_TOKENS.ink,
          }}
        >
          "My son helps me with calls. We're not interested. Don't call back."
        </div>
      </Letterhead>
      <div style={{ marginTop: 18, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: EG_TOKENS.alert,
            display: 'grid',
            placeItems: 'center',
            color: EG_TOKENS.paper,
            fontSize: 24,
            boxShadow: '0 8px 20px -8px rgba(196,83,59,0.5)',
          }}
        >
          ●
        </div>
      </div>
    </OBStep>
  );
}

export function OB4HandToMom({ nav }: { nav: Nav }) {
  return (
    <OBStep
      n={4}
      title="Now hand the phone to Mom."
      body="One last thing — I'll introduce myself to her in your voice."
      primary="Hand it over"
      secondary="Skip — I'll tell her later"
      onNext={() => nav('home')}
    >
      <Letterhead>
        <Eyebrow>What she'll hear</Eyebrow>
        <div
          style={{
            marginTop: 12,
            fontFamily: EG_FONTS.serif,
            fontSize: 19,
            lineHeight: 1.45,
            color: EG_TOKENS.ink,
          }}
        >
          "Hi Mom. I set up something on your phone. If a call feels weird,
          just tap the big button. I'll be right there."
        </div>
        <Signature style={{ marginTop: 14 }}>— Jarmar</Signature>
      </Letterhead>
    </OBStep>
  );
}

const page = {
  padding: '64px 28px 32px',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
} as const;

const fieldText = {
  marginTop: 8,
  fontFamily: EG_FONTS.serif,
  fontSize: 26,
  color: EG_TOKENS.ink,
  borderBottom: `1.5px solid ${EG_TOKENS.rule}`,
  paddingBottom: 6,
} as const;
