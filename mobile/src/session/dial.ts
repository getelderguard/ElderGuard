import { Linking } from 'react-native';

// Only a US E.164 number from our own backend is ever dialed. Anything else is refused rather
// than handed to the phone app, so a bad response cannot send the senior to another number.
const US_E164 = /^\+1\d{10}$/;

export function isGuardianLineNumber(n: unknown): n is string {
  return typeof n === 'string' && US_E164.test(n);
}

export async function dialGuardianLine(number: string): Promise<void> {
  if (!isGuardianLineNumber(number)) throw new Error('unexpected Guardian Line number');
  await Linking.openURL(`tel:${number}`);
}
