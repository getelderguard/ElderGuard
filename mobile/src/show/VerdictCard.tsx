import { View } from 'react-native';

import type { ShowResult } from '@/api/show';
import { Body, Card, EG_TOKENS, Eyebrow, Headline, PrimaryButton } from '@/design-system';

import { VERDICT_COPY } from './copy';

// The calmest verdict is plain, not green: it never reads as "safe".
export function VerdictCard({ result, onAgain }: { result: ShowResult; onAgain: () => void }) {
  const copy = VERDICT_COPY[result.verdict];
  const danger = result.verdict === 'dont_reply';
  const caution = result.verdict === 'be_careful';
  const color = danger ? EG_TOKENS.alert : caution ? EG_TOKENS.caution : EG_TOKENS.textMid;
  const wash = danger ? EG_TOKENS.alertWash : caution ? EG_TOKENS.cautionWash : EG_TOKENS.white;
  return (
    <View style={{ gap: 20 }} accessibilityLiveRegion="assertive">
      <Card style={{ backgroundColor: wash, gap: 12 }}>
        <Eyebrow color={color}>{copy.eyebrow}</Eyebrow>
        <Headline size={32} style={{ color }}>
          {copy.title}
        </Headline>
        <Body>{copy.body}</Body>
      </Card>
      <PrimaryButton danger={danger} onPress={onAgain}>
        Check something else
      </PrimaryButton>
    </View>
  );
}
