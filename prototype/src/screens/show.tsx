import {
  Body,
  EG_FONTS,
  EG_TOKENS,
  Eyebrow,
  FromLine,
  GhostLink,
  Headline,
  Letterhead,
  Phone,
  PrimaryButton,
  Signature,
  type Tone,
} from '../design-system';
import type { Nav } from '../navigator/types';

function ChoiceCard({ icon, label, onClick }: { icon: string; label: string; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: EG_TOKENS.card,
        borderRadius: 14,
        padding: '20px 14px',
        textAlign: 'center',
        boxShadow: '0 1px 0 rgba(31,39,71,0.08)',
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
      <div
        style={{
          fontFamily: EG_FONTS.serif,
          fontSize: 16,
          color: EG_TOKENS.ink,
        }}
      >
        {label}
      </div>
    </div>
  );
}

export function ShowEmpty({ nav }: { nav: Nav }) {
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
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 8,
          }}
        >
          <span
            onClick={() => nav('home')}
            style={{ fontSize: 22, color: EG_TOKENS.ink, cursor: 'pointer' }}
          >
            ‹
          </span>
          <Eyebrow>Back to home</Eyebrow>
        </div>
        <Headline size={28} style={{ marginTop: 4 }}>
          Show me what you got.
        </Headline>
        <Body size={15} style={{ marginTop: 10 }}>
          Paste it, snap a photo, or just describe it. I'll take a careful look.
        </Body>
        <div
          style={{
            marginTop: 22,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 10,
          }}
        >
          <ChoiceCard icon="📷" label="Take a photo" onClick={() => nav('show-q1')} />
          <ChoiceCard icon="📋" label="Paste text" onClick={() => nav('show-q1')} />
          <ChoiceCard icon="🎙" label="Say it aloud" onClick={() => nav('show-q1')} />
          <ChoiceCard icon="✉" label="Forward email" onClick={() => nav('show-q1')} />
        </div>
        <Letterhead tape={false} style={{ marginTop: 22 }}>
          <Body size={14} style={{ fontStyle: 'italic' }}>
            "If you're not sure — that's exactly when to show me. There's no
            such thing as bothering me."
          </Body>
          <Signature style={{ marginTop: 10 }}>— Jarmar</Signature>
        </Letterhead>
      </div>
    </Phone>
  );
}

type QProps = {
  n: number;
  total: number;
  q: string;
  options: { label: string; next: Parameters<Nav>[0] }[];
  nav: Nav;
};

function ShowQuestion({ n, total, q, options, nav }: QProps) {
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
        <Eyebrow style={{ color: EG_TOKENS.brass }}>
          Question {n} of {total}
        </Eyebrow>
        <Headline size={26} style={{ marginTop: 12 }}>
          {q}
        </Headline>
        <div
          style={{
            marginTop: 22,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          {options.map((o, i) => (
            <div
              key={i}
              onClick={() => nav(o.next)}
              style={{
                background: EG_TOKENS.card,
                border: `1.5px solid ${EG_TOKENS.rule}`,
                borderRadius: 14,
                padding: '16px 18px',
                fontSize: 15,
                color: EG_TOKENS.ink,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              {o.label}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 'auto', textAlign: 'center' }}>
          <GhostLink>I'm not sure</GhostLink>
        </div>
      </div>
    </Phone>
  );
}

export function ShowQ1({ nav }: { nav: Nav }) {
  return (
    <ShowQuestion
      n={1}
      total={2}
      q="Are they asking for money or info?"
      options={[
        { label: 'Yes — money', next: 'show-q2' },
        { label: 'Yes — personal info', next: 'show-q2' },
        { label: 'No, just chatting', next: 'show-q2' },
        { label: "I'm not sure", next: 'show-q2' },
      ]}
      nav={nav}
    />
  );
}

export function ShowQ2({ nav }: { nav: Nav }) {
  return (
    <ShowQuestion
      n={2}
      total={2}
      q="Did they say it's urgent?"
      options={[
        { label: 'Yes — right now', next: 'verdict-no' },
        { label: 'Sort of', next: 'verdict-care' },
        { label: 'No, no rush', next: 'verdict-ok' },
      ]}
      nav={nav}
    />
  );
}

type VerdictProps = {
  tone: Tone;
  eyebrow: string;
  title: string;
  body: string;
  action: string;
  nav: Nav;
};

function VerdictCard({ tone, eyebrow, title, body, action, nav }: VerdictProps) {
  const color =
    tone === 'alert'
      ? EG_TOKENS.alert
      : tone === 'caution'
      ? EG_TOKENS.caution
      : EG_TOKENS.ok;
  const wash =
    tone === 'alert'
      ? EG_TOKENS.alertWash
      : tone === 'caution'
      ? EG_TOKENS.cautionSoft
      : EG_TOKENS.okSoft;
  return (
    <Phone>
      <div
        style={{
          padding: '64px 24px 28px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: wash,
        }}
      >
        <Eyebrow style={{ color }}>{eyebrow}</Eyebrow>
        <Letterhead style={{ marginTop: 16 }}>
          <FromLine />
          <Headline size={28} style={{ marginTop: 14, color }}>
            {title}
          </Headline>
          <Body size={15} style={{ marginTop: 12 }}>
            {body}
          </Body>
          <Signature style={{ marginTop: 14 }}>— Jarmar</Signature>
        </Letterhead>
        <div
          style={{
            marginTop: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <PrimaryButton danger={tone === 'alert'} onClick={() => nav('home')}>
            {action}
          </PrimaryButton>
          <div style={{ textAlign: 'center' }}>
            <GhostLink onClick={() => nav('home')}>
              Tell Jarmar what you saw
            </GhostLink>
          </div>
        </div>
      </div>
    </Phone>
  );
}

export function VerdictLooksOK({ nav }: { nav: Nav }) {
  return (
    <VerdictCard
      tone="ok"
      eyebrow="Looks ok"
      title="Looks fine, Mom."
      body="Nothing in this matches what scammers usually do. You can reply if you want — but you don't have to."
      action="Got it"
      nav={nav}
    />
  );
}

export function VerdictBeCareful({ nav }: { nav: Nav }) {
  return (
    <VerdictCard
      tone="caution"
      eyebrow="Be careful"
      title="I'd be careful with this one."
      body="Some of it looks legit, but the urgency is a flag. Don't click any links. If you want, I'll loop in Jarmar."
      action="Loop in Jarmar"
      nav={nav}
    />
  );
}

export function VerdictDontReply({ nav }: { nav: Nav }) {
  return (
    <VerdictCard
      tone="alert"
      eyebrow="Don't reply"
      title="Don't reply, Mom."
      body="This one matches a scam I've seen before. Just delete it. I already told Jarmar — he's on it."
      action="Delete it"
      nav={nav}
    />
  );
}
