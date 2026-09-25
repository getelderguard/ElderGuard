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
  Signature,
} from '../design-system';
import type { Nav } from '../navigator/types';

export function HomeIdle({ nav }: { nav: Nav }) {
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
        <Eyebrow style={{ color: EG_TOKENS.brass }}>ElderGuard</Eyebrow>

        <Letterhead style={{ marginTop: 16 }}>
          <FromLine name="Jarmar" />
          <Headline size={26} style={{ marginTop: 16 }}>
            Hi Mom — I've got your back.
          </Headline>
          <Body size={15} style={{ marginTop: 10 }}>
            Tap whichever fits right now. I'm on standby if anything feels off.
          </Body>
          <Signature style={{ marginTop: 14 }}>— Jarmar</Signature>
        </Letterhead>

        <div
          style={{
            marginTop: 20,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 12,
          }}
        >
          <DoorCard
            icon="📞"
            title="On a call"
            sub="Tap to listen along"
            primary
            onClick={() => nav('call-clear')}
          />
          <DoorCard
            icon="✉"
            title="Got a message"
            sub="Text · email · letter"
            onClick={() => nav('show-empty')}
          />
        </div>

        <div
          style={{
            marginTop: 'auto',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingTop: 18,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: EG_TOKENS.ok,
              }}
            />
            <span
              style={{ fontSize: 12, color: EG_TOKENS.inkMuted, fontWeight: 600 }}
            >
              Jarmar · standby
            </span>
          </div>
          <GhostLink onClick={() => nav('profile')}>Profile</GhostLink>
        </div>
      </div>
    </Phone>
  );
}

type DoorCardProps = {
  icon: string;
  title: string;
  sub: string;
  primary?: boolean;
  onClick?: () => void;
};

function DoorCard({ icon, title, sub, primary, onClick }: DoorCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: EG_TOKENS.card,
        borderRadius: 18,
        padding: '22px 16px',
        textAlign: 'center',
        boxShadow:
          '0 1px 0 rgba(31,39,71,0.08), 0 12px 24px -16px rgba(31,39,71,0.18)',
        border: primary
          ? `1.5px solid ${EG_TOKENS.ink}`
          : '1.5px solid transparent',
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: primary ? EG_TOKENS.ink : EG_TOKENS.paper,
          color: primary ? EG_TOKENS.paper : EG_TOKENS.ink,
          display: 'grid',
          placeItems: 'center',
          fontSize: 22,
          margin: '0 auto 12px',
        }}
      >
        {icon}
      </div>
      <div
        style={{
          fontFamily: EG_FONTS.serif,
          fontSize: 20,
          fontWeight: 500,
          lineHeight: 1.1,
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: 12, color: EG_TOKENS.inkMuted, marginTop: 4 }}>
        {sub}
      </div>
    </div>
  );
}

export function ProfileScreen({ nav }: { nav: Nav }) {
  return (
    <Phone>
      <div
        style={{
          padding: '60px 24px 28px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}
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
          Settings & helpers
        </Headline>

        <div style={{ marginTop: 20 }}>
          <Eyebrow>You</Eyebrow>
          <Letterhead tape={false} style={{ marginTop: 8, padding: '4px 18px' }}>
            <Row label="Name" value="Eleanor" />
            <Row label="What you call yourself" value="Mom" last />
          </Letterhead>
        </div>

        <div style={{ marginTop: 20 }}>
          <Eyebrow>Helpers</Eyebrow>
          <Letterhead tape={false} style={{ marginTop: 8, padding: '4px 18px' }}>
            <Row label="Jarmar (son)" value="● Active" />
            <Row label="Add another helper" value="+" last />
          </Letterhead>
        </div>

        <div style={{ marginTop: 20 }}>
          <Eyebrow>Watching for</Eyebrow>
          <Letterhead tape={false} style={{ marginTop: 8, padding: '4px 18px' }}>
            <Row label="Tax threats, Medicare, tech support" value="Edit" last />
          </Letterhead>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: 16, textAlign: 'center' }}>
          <GhostLink>Pause ElderGuard</GhostLink>
        </div>
      </div>
    </Phone>
  );
}

function Row({
  label,
  value,
  last,
}: {
  label: string;
  value: string;
  last?: boolean;
}) {
  return (
    <div
      style={{
        padding: '16px 0',
        borderBottom: last ? 'none' : `1px solid ${EG_TOKENS.rule}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <span style={{ fontSize: 14, color: EG_TOKENS.inkSoft }}>{label}</span>
      <span
        style={{
          fontFamily: EG_FONTS.serif,
          fontSize: 16,
          color: EG_TOKENS.ink,
        }}
      >
        {value}
      </span>
    </div>
  );
}
