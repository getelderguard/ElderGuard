import { useEffect, useRef, useState } from 'react';

import { getSession, type PublicSession } from '@/api/sessions';

// Polls the backend rather than listening to Firestore: the session document also holds the
// model's free-text reason, and Firestore rules cannot hide one field from a reader.
const POLL_MS = 2500;
// While live the backend refreshes updated_at at least every 4 s. Silence longer than this
// means we have lost the call's state, and the screen must say so instead of showing the last tier.
const STALE_MS = 30_000;

export type LiveSession = {
  session: PublicSession | null;
  stale: boolean;
  error: Error | null;
};

export function useLiveSession(sessionId: string | undefined): LiveSession {
  const [session, setSession] = useState<PublicSession | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [now, setNow] = useState(() => Date.now());
  // Measured on this phone's clock, so server clock skew cannot hide staleness.
  const lastChange = useRef(Date.now());
  const lastUpdatedAt = useRef<number | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const s = await getSession(sessionId);
        if (cancelled) return;
        if (s.updated_at !== lastUpdatedAt.current) {
          lastUpdatedAt.current = s.updated_at;
          lastChange.current = Date.now();
        }
        setSession(s);
        setError(null);
        if (s.state === 'ended' || s.state === 'expired') return;
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e : new Error(String(e)));
      }
      if (!cancelled) timer = setTimeout(tick, POLL_MS);
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const active = session?.state === 'live' || session?.state === 'reconnecting';
  const stale = active && now - lastChange.current > STALE_MS;
  return { session, stale, error };
}
