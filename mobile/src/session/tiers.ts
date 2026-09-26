// Live-call tiers, mirroring backend/app/scoring/tiers.py. There is deliberately no "safe"
// tier while a call is live: Listening never asserts safety.
export type Tier = 'listening' | 'caution' | 'stop' | 'unknown' | 'no_audio';
