import type { Tier } from '@/session/tiers';

import { api } from './client';

export type SessionState = 'pending' | 'ringing' | 'live' | 'reconnecting' | 'ended' | 'expired';

// Mirrors Session.public_view() in the backend. The model's free-text reason is deliberately
// absent: a caller can steer it, so the senior's phone never receives it.
export type PublicSession = {
  id: string;
  state: SessionState;
  initiated_by: 'app' | 'line';
  tier: Tier;
  dial: number;
  score: number | null;
  flags: string[];
  max_score: number;
  updated_at: number;
  live_at: number | null;
  ended_at: number | null;
};

export type Intent = {
  session_id: string;
  guardian_line_number: string;
  expires_at: number;
};

export const createIntent = () => api<Intent>('POST', '/v1/sessions/intent');
export const getSession = (id: string) => api<PublicSession>('GET', `/v1/sessions/${encodeURIComponent(id)}`);
export const sendFeedback = (id: string, falseAlarm: boolean, note = '') =>
  api<void>('POST', `/v1/sessions/${encodeURIComponent(id)}/feedback`, { false_alarm: falseAlarm, note });
