import type { Tier } from './tiers';

// Every word the senior sees during a call comes from here. Nothing from the model or the
// caller is ever shown, so nobody on the line can put words on this screen.
export const TIER_COPY: Record<Tier | 'stale' | 'connecting', { title: string; body: string }> = {
  connecting: {
    title: 'Waiting for the merge',
    body: 'Tap Merge Calls on your phone screen. Then come back here.',
  },
  listening: {
    title: 'Listening with you',
    body: 'Keep going. I will tell you if something sounds wrong. Never share money or codes.',
  },
  caution: {
    title: 'Be careful',
    body: 'Do not give money, gift cards, codes, or personal details. It is fine to hang up.',
  },
  stop: {
    title: 'Hang up now',
    body: 'This sounds like a scam. Hang up. You did nothing wrong.',
  },
  unknown: {
    title: 'I lost my hearing for a second',
    body: 'Still listening. Until I am back, do not share money or codes.',
  },
  no_audio: {
    title: 'I cannot hear the call',
    body: 'Did you tap Merge Calls? Until I can hear, do not share money or codes.',
  },
  stale: {
    title: 'Checking the connection',
    body: 'I may have lost the call. Do not share money or codes. You can always hang up.',
  },
};
