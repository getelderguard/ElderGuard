import { api } from './client';

// The consent text in src/app/(setup)/consent.tsx is this version. The backend rejects any other
// with 409, which means the app is out of date and must not claim agreement to text it never showed.
export const CONSENT_VERSION = '2026-09-25';

export type Account = {
  id: string;
  senior: { display_name: string; nickname: string; phone_last4: string; consent_version: string };
  watch_list: string[];
};

export const getMe = () => api<Account>('GET', '/v1/accounts/me');

export const enroll = (displayName: string, nickname: string) =>
  api<Account>('POST', '/v1/accounts/me', {
    display_name: displayName,
    nickname,
    consent_version: CONSENT_VERSION,
    watch_list: [],
  });
