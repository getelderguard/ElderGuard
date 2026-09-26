import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { getMe, type Account } from '@/api/accounts';
import { devAuthActive, setAuthProvider } from '@/api/auth';
import { ApiError } from '@/api/client';

import { bearerFor, signOut as firebaseSignOut, watchUser, type User } from './firebase';

// loading: waiting on Firebase or the backend. signed_out: no phone sign-in yet.
// needs_setup: signed in, not enrolled. ready: enrolled. offline: could not reach the backend.
export type AuthPhase = 'loading' | 'signed_out' | 'needs_setup' | 'ready' | 'offline';

type AuthState = {
  phase: AuthPhase;
  account: Account | null;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

type Check = { uid: string; phase: 'needs_setup' | 'ready' | 'offline'; account: Account | null };

const DEV_UID = 'dev';
const Ctx = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthGate');
  return v;
}

async function checkAccount(uid: string): Promise<Check> {
  try {
    return { uid, phase: 'ready', account: await getMe() };
  } catch (e) {
    const phase = e instanceof ApiError && e.status === 404 ? 'needs_setup' : 'offline';
    return { uid, phase, account: null };
  }
}

export function AuthGate({ children }: { children: ReactNode }) {
  const dev = devAuthActive();
  // undefined until Firebase reports; dev builds with dev headers skip Firebase entirely.
  const [uid, setUid] = useState<string | null | undefined>(dev ? DEV_UID : undefined);
  const [check, setCheck] = useState<Check | null>(null);

  useEffect(() => {
    if (dev) return;
    return watchUser((u: User | null) => {
      setAuthProvider(u ? bearerFor(u) : null);
      setUid(u?.uid ?? null);
    });
  }, [dev]);

  useEffect(() => {
    if (!uid) return;
    let live = true;
    checkAccount(uid).then((c) => live && setCheck(c));
    return () => {
      live = false;
    };
  }, [uid]);

  const refresh = useCallback(async () => {
    if (uid) setCheck(await checkAccount(uid));
  }, [uid]);

  const signOut = useCallback(async () => {
    if (!dev) await firebaseSignOut();
  }, [dev]);

  // A check for a previous user never applies to the current one.
  const current = uid && check?.uid === uid ? check : null;
  const phase: AuthPhase =
    uid === undefined ? 'loading' : uid === null ? 'signed_out' : (current?.phase ?? 'loading');

  return (
    <Ctx.Provider value={{ phase, account: current?.account ?? null, refresh, signOut }}>{children}</Ctx.Provider>
  );
}
