import {
  getAuth,
  getIdToken,
  onAuthStateChanged,
  signInWithPhoneNumber,
  signOut as firebaseSignOut,
  type ConfirmationResult,
  type User,
} from '@react-native-firebase/auth';

export type { User };

// US numbers only: the Firebase project allows SMS to the US alone, and the Guardian Line is a
// US number. Accepts "(555) 123-4567", "555.123.4567", "+1 555 123 4567".
export function toUsE164(input: string): string | null {
  const digits = input.replace(/\D/g, '');
  const ten = digits.length === 11 && digits.startsWith('1') ? digits.slice(1) : digits;
  if (!/^[2-9]\d{2}[2-9]\d{6}$/.test(ten)) return null;
  return `+1${ten}`;
}

// The code screen needs the confirmation from the phone screen. It holds a verification id,
// not a secret, and lives only in memory.
let pending: { phone: string; confirmation: ConfirmationResult } | null = null;

export async function sendCode(phoneE164: string): Promise<void> {
  const confirmation = await signInWithPhoneNumber(getAuth(), phoneE164);
  pending = { phone: phoneE164, confirmation };
}

export function pendingPhone(): string | null {
  return pending?.phone ?? null;
}

export async function confirmCode(code: string): Promise<void> {
  if (!pending) throw Object.assign(new Error('no code sent'), { code: 'auth/session-expired' });
  await pending.confirmation.confirm(code);
  pending = null;
}

export function watchUser(cb: (user: User | null) => void): () => void {
  return onAuthStateChanged(getAuth(), cb);
}

export function bearerFor(user: User) {
  // getIdToken returns the cached token and refreshes it shortly before it expires.
  return async () => ({ Authorization: `Bearer ${await getIdToken(user)}` });
}

export async function signOut(): Promise<void> {
  pending = null;
  await firebaseSignOut(getAuth());
}

// Plain words for the Firebase errors a senior can actually hit.
export function explainAuthError(e: unknown): string {
  const code = (e as { code?: string })?.code ?? '';
  switch (code) {
    case 'auth/invalid-phone-number':
      return 'That number does not look right. Please check it.';
    case 'auth/invalid-verification-code':
      return 'That code is not right. Please check the text message and try again.';
    case 'auth/session-expired':
    case 'auth/code-expired':
      return 'That code has expired. Go back and send a new one.';
    case 'auth/too-many-requests':
    case 'auth/quota-exceeded':
      return 'Too many tries for now. Please wait a while and try again.';
    case 'auth/network-request-failed':
      return 'No internet connection. Please check Wi-Fi or data and try again.';
    default:
      return 'Something went wrong. Please try again.';
  }
}
