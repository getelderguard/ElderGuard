// The backend the app talks to. Forks set EXPO_PUBLIC_API_BASE_URL at build time.
const DEFAULT_API = 'https://api.getelderguard.org';

function resolveBaseUrl(): string {
  const raw = (process.env.EXPO_PUBLIC_API_BASE_URL ?? DEFAULT_API).replace(/\/+$/, '');
  // Plain http is only for a local dev backend. A release build must never send tokens in clear.
  if (!__DEV__ && !raw.startsWith('https://')) {
    throw new Error('EXPO_PUBLIC_API_BASE_URL must be https in release builds');
  }
  return raw;
}

export const API_BASE_URL = resolveBaseUrl();
