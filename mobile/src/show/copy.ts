import type { Verdict } from '@/api/show';

// Every word the senior sees about a message comes from here. Nothing from the model or from the
// message itself is ever shown, so nobody who wrote the message can put words on this screen.
// No verdict says "safe": the calmest one still tells her what to do if she is unsure.
export const VERDICT_COPY: Record<Verdict, { eyebrow: string; title: string; body: string; action: string }> = {
  no_red_flags: {
    eyebrow: 'No warning signs found',
    title: 'I did not see the usual scam signs.',
    body: 'That does not prove it is safe. If it asks for money, codes, or personal details, or if you feel unsure, ask someone you trust before you reply.',
    action: 'Done',
  },
  be_careful: {
    eyebrow: 'Be careful',
    title: 'I would be careful with this one.',
    body: 'Some things in it look like a scam. Do not click any links, send money, or share codes. Check with someone you trust before you reply.',
    action: 'Done',
  },
  dont_reply: {
    eyebrow: 'Do not reply',
    title: 'Do not reply to this.',
    body: 'This looks like a scam. Do not click anything, call any number in it, or send money. You can delete it. You did nothing wrong.',
    action: 'Done',
  },
};

// Reasons we could not check. None of them is a calm answer.
export const NOT_CHECKED_TIP = 'If you are unsure, do not reply, and ask someone you trust.';
