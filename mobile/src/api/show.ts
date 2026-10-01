import { api } from './client';

// Mirrors backend/app/api/show.py. The server enforces these; the app checks first so a senior
// is not left waiting on an upload that is certain to be refused.
export const MAX_TEXT_CHARS = 4000;
export const MAX_IMAGE_BYTES = 3_500_000;

// The server allows its provider 25 s, and it may try a fallback.
const CHECK_TIMEOUT_MS = 40_000;

// There is no "safe" verdict: the calmest one only says no warning signs were found.
export type Verdict = 'no_red_flags' | 'be_careful' | 'dont_reply';

// The model's free-text reasoning is deliberately absent: a stranger's message can steer it, so
// the senior's phone never receives it.
export type ShowResult = { verdict: Verdict; flags: string[] };

export const checkMessage = (input: { text: string; imageB64: string | null }) =>
  api<ShowResult>(
    'POST',
    '/v1/show/check',
    { text: input.text, image_b64: input.imageB64 },
    CHECK_TIMEOUT_MS,
  );

// Size of the decoded picture, from the base64 length.
export const imageBytes = (b64: string) => Math.floor((b64.length * 3) / 4);
