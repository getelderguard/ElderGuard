import { useState, type ReactNode } from 'react';
import type { ScreenId } from './types';
import {
  OB1Relationship,
  OB2Vulnerabilities,
  OB3VoiceScript,
  OB4HandToMom,
  OBSplash,
} from '../screens/onboarding';
import { HomeIdle, ProfileScreen } from '../screens/home';
import {
  CallCaution,
  CallChecking,
  CallClear,
  CallFalseAlarm,
  CallTakeover,
  CallTakeoverNoVoice,
} from '../screens/call';
import {
  ShowEmpty,
  ShowQ1,
  ShowQ2,
  VerdictBeCareful,
  VerdictDontReply,
  VerdictLooksOK,
} from '../screens/show';

type Entry = { id: ScreenId; label: string; group: string };

const SCREENS: Entry[] = [
  { id: 'ob-splash', label: '01 · Splash', group: 'Onboarding' },
  { id: 'ob-1', label: '02 · Who', group: 'Onboarding' },
  { id: 'ob-2', label: '03 · Watch for', group: 'Onboarding' },
  { id: 'ob-3', label: '04 · Voice + script', group: 'Onboarding' },
  { id: 'ob-4', label: '05 · Hand to Mom', group: 'Onboarding' },
  { id: 'home', label: '06 · Home', group: 'Home' },
  { id: 'profile', label: '13 · Profile', group: 'Home' },
  { id: 'call-clear', label: '07 · All clear', group: 'Call' },
  { id: 'call-caution', label: '08 · Caution', group: 'Call' },
  { id: 'call-checking', label: '09 · Checking', group: 'Call' },
  { id: 'call-takeover', label: '10 · Takeover (voice)', group: 'Call' },
  { id: 'call-noVoice', label: '11 · Takeover · read', group: 'Call' },
  { id: 'call-falseAlarm', label: '12 · False alarm', group: 'Call' },
  { id: 'show-empty', label: '14 · Empty', group: 'Show me' },
  { id: 'show-q1', label: '15 · Question 1', group: 'Show me' },
  { id: 'show-q2', label: '16 · Question 2', group: 'Show me' },
  { id: 'verdict-ok', label: '17 · Looks ok', group: 'Show me' },
  { id: 'verdict-care', label: '18 · Be careful', group: 'Show me' },
  { id: 'verdict-no', label: "19 · Don't reply", group: 'Show me' },
];

export function Navigator() {
  const [screen, setScreen] = useState<ScreenId>('ob-splash');
  const [dockOpen, setDockOpen] = useState(false);

  const nav = (id: ScreenId) => {
    setScreen(id);
    setDockOpen(false);
  };

  return (
    <div style={shell}>
      <Stage>{render(screen, nav)}</Stage>
      <DockToggle open={dockOpen} onClick={() => setDockOpen((v) => !v)} />
      {dockOpen && <Dock current={screen} onPick={nav} />}
    </div>
  );
}

function render(id: ScreenId, nav: (id: ScreenId) => void): ReactNode {
  switch (id) {
    case 'ob-splash':       return <OBSplash nav={nav} />;
    case 'ob-1':            return <OB1Relationship nav={nav} />;
    case 'ob-2':            return <OB2Vulnerabilities nav={nav} />;
    case 'ob-3':            return <OB3VoiceScript nav={nav} />;
    case 'ob-4':            return <OB4HandToMom nav={nav} />;
    case 'home':            return <HomeIdle nav={nav} />;
    case 'profile':         return <ProfileScreen nav={nav} />;
    case 'call-clear':      return <CallClear nav={nav} />;
    case 'call-caution':    return <CallCaution nav={nav} />;
    case 'call-checking':   return <CallChecking nav={nav} />;
    case 'call-takeover':   return <CallTakeover nav={nav} />;
    case 'call-noVoice':    return <CallTakeoverNoVoice nav={nav} />;
    case 'call-falseAlarm': return <CallFalseAlarm nav={nav} />;
    case 'show-empty':      return <ShowEmpty nav={nav} />;
    case 'show-q1':         return <ShowQ1 nav={nav} />;
    case 'show-q2':         return <ShowQ2 nav={nav} />;
    case 'verdict-ok':      return <VerdictLooksOK nav={nav} />;
    case 'verdict-care':    return <VerdictBeCareful nav={nav} />;
    case 'verdict-no':      return <VerdictDontReply nav={nav} />;
  }
}

function Stage({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        flex: 1,
        display: 'grid',
        placeItems: 'center',
        padding: '24px 16px',
        overflow: 'auto',
      }}
    >
      {children}
    </div>
  );
}

function DockToggle({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 100,
        padding: '10px 14px',
        background: '#f5ede0',
        color: '#1f2747',
        border: 'none',
        borderRadius: 999,
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        cursor: 'pointer',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
      }}
    >
      {open ? 'Close' : 'Screens'}
    </button>
  );
}

function Dock({
  current,
  onPick,
}: {
  current: ScreenId;
  onPick: (id: ScreenId) => void;
}) {
  const groups: Record<string, Entry[]> = {};
  for (const s of SCREENS) {
    (groups[s.group] ||= []).push(s);
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(20,18,15,0.88)',
        backdropFilter: 'blur(6px)',
        zIndex: 90,
        overflow: 'auto',
        padding: '32px 20px 96px',
        color: '#f5ede0',
        fontFamily:
          "'Public Sans', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <div style={{ maxWidth: 540, margin: '0 auto' }}>
        <div
          style={{
            fontSize: 11,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: '#c89b5b',
            fontWeight: 700,
          }}
        >
          ElderGuard · Jump to screen
        </div>
        <div
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 28,
            fontWeight: 500,
            marginTop: 4,
          }}
        >
          All 19 screens
        </div>

        {Object.entries(groups).map(([group, items]) => (
          <div key={group} style={{ marginTop: 24 }}>
            <div
              style={{
                fontSize: 11,
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color: 'rgba(245,237,224,0.55)',
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              {group}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {items.map((s) => {
                const active = s.id === current;
                return (
                  <button
                    key={s.id}
                    onClick={() => onPick(s.id)}
                    style={{
                      textAlign: 'left',
                      padding: '12px 14px',
                      background: active ? '#f5ede0' : 'transparent',
                      color: active ? '#1f2747' : '#f5ede0',
                      border: '1.5px solid rgba(245,237,224,0.18)',
                      borderRadius: 10,
                      fontSize: 14,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    {s.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const shell = {
  position: 'relative',
  minHeight: '100%',
  display: 'flex',
  flexDirection: 'column',
  background: '#1a1814',
} as const;
