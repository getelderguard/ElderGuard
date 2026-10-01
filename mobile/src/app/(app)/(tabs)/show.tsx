import { useState } from 'react';
import { Image, KeyboardAvoidingView, Platform, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiAuthMissing } from '@/api/auth';
import { ApiError } from '@/api/client';
import { checkMessage, MAX_TEXT_CHARS, type ShowResult } from '@/api/show';
import {
  Body,
  Card,
  EG_TOKENS,
  GhostLink,
  Headline,
  PrimaryButton,
  SecondaryButton,
  Shield,
  TextField,
  Wordmark,
} from '@/design-system';
import { NOT_CHECKED_TIP } from '@/show/copy';
import { usePicture } from '@/show/usePicture';
import { VerdictCard } from '@/show/VerdictCard';

function explain(e: unknown): string {
  if (e instanceof ApiAuthMissing) return 'Please sign in first.';
  if (e instanceof ApiError) {
    if (e.status === 429) return 'You have checked a lot just now. Please wait a few minutes and try again.';
    if (e.status === 413) return 'That picture is too large. Try a smaller one.';
    if (e.status === 415) return 'That kind of file cannot be checked. Try a screenshot or a photo.';
    if (e.status === 404) return 'This phone is not set up with ElderGuard yet.';
    if (e.status === 503) return 'Show me is paused right now.';
  }
  return 'ElderGuard could not check this just now.';
}

// Show me: paste a message, or add a screenshot or photo, and get a plain-language answer.
// Nothing is kept: the text and picture live in this screen's memory until she leaves or starts over.
export default function Show() {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [result, setResult] = useState<ShowResult | null>(null);
  const pic = usePicture();

  const reset = () => {
    setText('');
    pic.clear();
    setProblem(null);
    setResult(null);
  };

  const check = async () => {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      setResult(await checkMessage({ text: text.trim(), imageB64: pic.picture?.b64 ?? null }));
    } catch (e) {
      // Never a calm answer when the check did not happen.
      setProblem(`${explain(e)} ${NOT_CHECKED_TIP}`);
    } finally {
      setBusy(false);
    }
  };

  const ready = text.trim().length > 0 || pic.picture !== null;
  const shownProblem = problem ?? pic.problem;

  return (
    // The tab bar already sits above the bottom inset.
    <SafeAreaView edges={['top', 'left', 'right']} style={{ flex: 1, backgroundColor: EG_TOKENS.sand }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1, padding: 24, gap: 24 }}>
          <Wordmark />
          {result ? (
            <VerdictCard result={result} onAgain={reset} />
          ) : (
            <>
              <View style={{ gap: 12, alignItems: 'center' }}>
                <Shield size={56} />
                <Headline style={{ textAlign: 'center' }}>Got a message that seems odd?</Headline>
                <Body style={{ textAlign: 'center' }}>
                  Paste it here, or add a screenshot or a photo of a letter. ElderGuard will take a careful look.
                </Body>
              </View>

              <TextField
                label="The message"
                value={text}
                onChangeText={setText}
                multiline
                maxLength={MAX_TEXT_CHARS}
                placeholder="Press and hold here, then tap Paste"
                autoCorrect={false}
                accessibilityHint="Paste the text of the message you are unsure about"
                style={{ minHeight: 140, paddingTop: 14, textAlignVertical: 'top', fontSize: 19 }}
              />

              {pic.picture ? (
                <Card style={{ gap: 14, alignItems: 'center', paddingTop: 22 }}>
                  <Image
                    source={{ uri: pic.picture.uri }}
                    accessibilityLabel="The picture you added"
                    style={{ width: '100%', height: 220, borderRadius: 8 }}
                    resizeMode="contain"
                  />
                  <GhostLink onPress={pic.clear} accessibilityHint="Removes the picture you added">
                    Remove this picture
                  </GhostLink>
                </Card>
              ) : (
                <View style={{ gap: 12 }}>
                  <SecondaryButton onPress={pic.choose} disabled={busy} accessibilityHint="Choose a screenshot from your phone">
                    Add a screenshot
                  </SecondaryButton>
                  <SecondaryButton onPress={pic.photograph} disabled={busy} accessibilityHint="Take a photo of a letter or a screen">
                    Take a photo
                  </SecondaryButton>
                </View>
              )}

              {shownProblem && (
                <View accessibilityLiveRegion="polite">
                  <Body style={{ color: EG_TOKENS.alert }}>{shownProblem}</Body>
                </View>
              )}

              <View style={{ gap: 12 }}>
                <PrimaryButton
                  onPress={check}
                  disabled={busy || !ready}
                  accessibilityHint="Checks the message and tells you if it looks like a scam"
                >
                  {busy ? 'Looking…' : 'Check it'}
                </PrimaryButton>
                <Body size={15} style={{ textAlign: 'center' }}>
                  Nothing you add is saved. It is looked at once, then forgotten.
                </Body>
              </View>
            </>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
