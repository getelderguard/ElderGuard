// Where request credentials come from. The signed-in Firebase user plugs in here
// (setAuthProvider, from src/auth/AuthGate); dev builds can use the backend's dev-auth headers.
export type AuthProvider = () => Promise<Record<string, string>>;

let provider: AuthProvider | null = null;

export function setAuthProvider(p: AuthProvider | null) {
  provider = p;
}

// Dev auth: the backend accepts X-Dev-Uid / X-Dev-Phone only when AUTH_MODE=dev and never in prod.
function devProvider(): AuthProvider | null {
  if (!__DEV__) return null;
  const uid = process.env.EXPO_PUBLIC_DEV_UID;
  if (!uid) return null;
  const phone = process.env.EXPO_PUBLIC_DEV_PHONE ?? '';
  return async () => ({ 'X-Dev-Uid': uid, ...(phone ? { 'X-Dev-Phone': phone } : {}) });
}

// True when a dev build talks to a local backend with dev headers instead of Firebase.
export function devAuthActive(): boolean {
  return devProvider() !== null;
}

export async function authHeaders(): Promise<Record<string, string>> {
  const p = provider ?? devProvider();
  if (!p) throw new ApiAuthMissing();
  return p();
}

export class ApiAuthMissing extends Error {
  constructor() {
    super('not signed in');
  }
}
