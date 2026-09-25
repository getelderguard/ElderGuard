# Legal notes for the lawyer hour

This is not legal advice. It is the maintainer's homework so that the one to two hours with a telecom and privacy lawyer are spent on decisions, not on explaining the product. Where a detail is uncertain it says "verify." Nothing here has been reviewed by counsel yet. **No user other than the maintainer uses the live guardian until that review happens.**

## What the product does, technically

1. A senior receives or makes an ordinary phone call.
2. They tap a button. Their phone dials a phone number ElderGuard owns (a Twilio number, the "Guardian Line"). Their carrier puts the first call on hold.
3. The senior taps the native "Merge Calls" button. The carrier joins the three legs. ElderGuard's line now hears both the senior and the far party.
4. Before the merge, while only the senior is on our leg, a short spoken instruction plays ("press Merge Calls now").
5. After the merge, by default, a short spoken notice plays to everyone on the call that the call is protected by ElderGuard. This is a feature flag that is on by default (`Flags.announcement`). Playback is planned for M1; the flag exists today.
6. Audio is streamed to a transcription provider (Deepgram) in real time. The text is scored every few seconds by an LLM (Anthropic). A tier (Listening, Caution, Stop) is shown in the senior's app and, for app-initiated sessions, pushed to a linked family member.
7. On Stop, a pre-recorded line in the family member's own voice can be played into the call (M3).
8. **No recording is made.** No audio and no transcript are stored anywhere. See `docs/DATA-RETENTION.md`.
9. The senior accepted a versioned consent screen at onboarding (M2) explaining all of the above.

The operator is the person or organisation running the backend. Today that is the maintainer, self-funded. The intent is a non-profit organisation with the app free to seniors.

## The consent problem

Real-time listening by a third party is "interception" or "eavesdropping" under wiretap statutes even when nothing is recorded. The fact that a machine rather than a person listens does not obviously change that; the fact that the senior invited the listener does, in one-party states.

**Federal.** The Wiretap Act, 18 U.S.C. § 2511(2)(d), permits interception where one party to the communication has given prior consent, unless the interception is for a criminal or tortious purpose. The senior is a party and consents. Federal law is therefore satisfied by the senior's onboarding consent. Verify that "party" clearly covers the senior when the interception is performed by a third-party service they engaged.

**States.** Roughly a dozen states require all parties to consent to interception or recording of a private communication. The list commonly cited: California, Delaware, Florida, Illinois, Maryland, Massachusetts, Montana, Nevada, New Hampshire, Oregon, Pennsylvania, Washington. Classifications vary by source and by whether the statute covers eavesdropping or only recording, in-person or telephone, and criminal or civil exposure. Known quirks to verify with counsel:

- **Oregon** is all-party for in-person conversations but one-party for telephone calls (ORS 165.540). Verify.
- **Connecticut** is one-party under the criminal statute but has a civil all-party rule for telephone recording (Conn. Gen. Stat. § 52-570d). Verify.
- **Michigan** courts have read the eavesdropping statute to permit a participant to record. Verify current status.
- **Illinois** was amended in 2014 after its old statute was struck down; the current statute turns on whether the conversation is "private." Verify.
- **Nevada** has been treated as all-party for telephone calls by its supreme court. Verify.

**California.** Penal Code § 632 makes it a crime to intentionally, without the consent of all parties, use an electronic device to eavesdrop upon or record a confidential communication. § 632.7 covers communications involving a cellular or cordless phone without regard to confidentiality. § 632 penalises eavesdropping, not only recording, which is why "we only analyse, we don't store" is not a defence. § 633.5 lets one party record to obtain evidence reasonably believed to relate to extortion, kidnapping, bribery, a violent felony, or § 653m (harassing calls). Whether a senior who suspects a scam falls under § 633.5 for a scam that has not yet been identified is a question for counsel; do not rely on it. § 637.2 gives a private right of action with statutory damages. Kearney v. Salomon Smith Barney, Inc., 39 Cal. 4th 95 (2006) applied California law to calls made from Georgia into California, so a senior anywhere talking to someone in California is exposed to California's rule, and the operator cannot know where the far party is.

**Washington.** RCW 9.73.030(1) requires the consent of all participants to intercept or record a private communication by telephone. RCW 9.73.030(3) provides that consent is considered obtained when one party has announced to all other parties, in a reasonably effective manner, that the communication is about to be recorded or transmitted, and the announcement itself is recorded or transmitted. This is the clearest statutory basis for the announcement design, and the reason the announcement must play *before* scoring starts on the merged audio, not after. Verify whether "transmitted" covers real-time streaming to a transcription service.

**Consequence.** Because the far party's location is unknown, the only design that is defensible everywhere is one that obtains the far party's consent on every call. The announcement does that, and a party who stays on the line after it has consented under the usual implied-consent reasoning. Whether implied consent by staying on the line satisfies every all-party state is question 1 for counsel.

## The announcement design

The announcement is on by default. It plays once, right after the merge is detected, in a neutral voice: "This call is protected by ElderGuard." Framed as a feature: scammers hang up on monitored calls, real callers do not mind.

Precedent the maintainer relies on for the "this is normal" argument, to be verified by counsel rather than treated as law:

- Apple's Phone app call recording (iOS 18 and later) plays an announcement to all parties when recording begins.
- Google's Phone app call recording announces to all parties at the start and end of recording.
- Contact centres play "this call may be monitored or recorded" as a standard practice, and RCW 9.73.030(3) is one statute that explicitly blesses it.

Design decisions that follow:

- The announcement plays before any merged audio is scored. The evidence gate (`app/scoring/evidence.py`) already prevents any tier change in the first 15 seconds; M1 plays the announcement at merge detection.
- A "silent mode" is not offered in v1. If counsel advises that silent operation is lawful for seniors in one-party states, it becomes an opt-in behind a second consent screen, never the default.
- The senior's consent is versioned (`consent_version`, `consent_at` on the account) so that a change in the announcement or the data practices forces re-consent.
- A fork that turns the announcement off assumes this exposure. `docs/THREAT-MODEL.md` says so.

## Voice, biometrics, and BIPA

The Illinois Biometric Information Privacy Act, 740 ILCS 14, treats a "voiceprint" as a biometric identifier and requires written informed consent, a retention schedule, and a destruction policy, with statutory damages per violation. Texas (Tex. Bus. & Com. Code § 503.001) and Washington (RCW 19.375) have similar laws without the private right of action. Verify current amendments to BIPA's damages provisions.

v1 avoids the question rather than answering it:

- No voice cloning. The guardian records fixed template lines ("It's Jarmar. Hang up now.") on their own device. The clip is played back as-is. No model of the guardian's voice is created.
- No speaker identification. The transcript is unlabelled mixed audio; no voiceprint of the senior or the far party is derived.
- The clips are stored in a private bucket, deletable by the guardian, and deleted with the account (`docs/DATA-RETENTION.md`).

Whether a raw recording of a person saying a sentence is itself a "voiceprint" under BIPA is a question for counsel. The maintainer's reading is no, because it is not used to identify anyone. Voice cloning (roadmap) would reopen this and needs a BIPA-compliant consent flow before it is built.

## TCPA and A2P 10DLC

The Telephone Consumer Protection Act, 47 U.S.C. § 227, restricts calls and texts made with automatic dialling systems or prerecorded voices without prior express consent. In v1:

- ElderGuard makes no outbound calls. The senior dials the Guardian Line; our line never dials anyone.
- ElderGuard sends no SMS. The only SMS is the Firebase Authentication one-time code, which the user requests by entering their number.
- Push notifications are not TCPA communications.

If a future version sends SMS to guardians ("Mom's call hit Stop"), the operator needs the guardian's prior express consent (collected at link time), an opt-out mechanism, and carrier A2P 10DLC brand and campaign registration through Twilio before US carriers will deliver the messages. Backend-initiated calls (Twilio Conference dialling the senior) would be calls placed by us and would need the same analysis; they are explicitly out of scope for v1.

## HIPAA

ElderGuard is not a covered entity (not a health plan, clearinghouse, or provider) and not a business associate of one. Calls will contain protected health information when the caller is a doctor's office or pharmacy. The design response is to store nothing: no audio, no transcript, no reasoning text visible to anyone but a guardian, and the reasoning is capped at 240 characters. Verify that no state health-privacy law (California CMIA, for example) reaches a consumer app that processes but does not store such information.

## COPPA

Not applicable. The product is for adults. Store listings are rated for adults; the app does not knowingly collect information from anyone under 13. If a guardian under 18 is linked (a grandchild), verify whether any state minor-consent rule applies to their name and phone number.

## Elder abuse reporting

Every state has adult protective services and a list of mandatory reporters of elder abuse, including financial abuse. In California, Welfare and Institutions Code § 15630 lists care custodians, health practitioners, clergy, and employees of financial institutions, among others. A software application and its operator are not on these lists, and the operator never has enough information to make a report (no names of callers, no stored content). ElderGuard therefore does not report, and the terms should say that it is not a substitute for reporting to APS or law enforcement. The app should surface the FTC (reportfraud.ftc.gov) and the National Elder Fraud Hotline (833-372-8311; verify number) after a Stop.

## The AI's advice and liability

ElderGuard tells a senior to hang up. Sometimes it will be wrong. Two directions of error, two kinds of exposure:

- **False Stop.** The senior hangs up on a real doctor, bank, or relative. Harm is embarrassment or a missed call. Mitigated by the two-signal Stop rule, the evidence gate, and the false-alarm feedback screen.
- **False Listening.** ElderGuard stays quiet during a real scam and the senior loses money. Harm is the loss and a claim that the senior relied on ElderGuard. Mitigated by never having a "safe" tier, by the fallback notice that tells the senior to hang up if anything feels wrong, and by the terms.

47 U.S.C. § 230 protects providers from liability for information provided by another information content provider. The AI's guidance is generated by the operator's own system, so § 230 should be assumed not to apply. The relevant frameworks are negligence, product liability, and consumer-protection (unfair or deceptive practices) law. Questions for counsel: what the terms must say about accuracy and reliance, whether an arbitration clause is appropriate for a free service to seniors, and whether describing the product as "detecting scams" in marketing creates an implied warranty.

## App Store and Google Play requirements

**Apple App Review Guidelines.** 5.1.1 (Data Collection and Storage): a privacy policy link in the listing and in the app; consent before collecting data; the app must work without optional data; account deletion in the app if the app supports account creation. 5.1.2 (Data Use and Sharing): no repurposing of data; disclose third-party processors (Deepgram, Anthropic, Twilio, Google); no tracking without ATT (we track nothing). Also relevant: 2.5.14 (no recording of the screen or calls without notification), 4.0 (design), and the Health and Medical guidance if the app is marketed to seniors' caregivers. Verify the current numbering.

**Google Play.** User Data policy: a privacy policy in the listing and in-app; prominent disclosure and runtime consent before collecting sensitive data (audio, contacts write); a Data Safety form matching `docs/DATA-RETENTION.md`; an account-deletion web URL (the data-deletion page). Permissions policy: `CALL_PHONE` must be justified in the listing (it lets the app dial the Guardian Line without an extra tap); the app must not be a default dialer replacement in v1. Also review the Call Log and SMS permissions policy to confirm neither is requested.

**Store demo mode.** Reviewers get `FAKE_PROVIDERS=1` against a separate instance plus a review video. The listing must say that the live guardian requires a phone plan that supports three-way calling.

## Terms of service must-haves

- The service is provided as-is, free of charge, and is not a guarantee against fraud.
- ElderGuard's guidance is generated by automated systems and can be wrong in both directions. The user remains responsible for their decisions.
- The user represents they will use the guardian only on calls where they are a party, and understands an announcement will play to the other party.
- Description of what is and is not stored, by reference to the privacy policy.
- No emergency service. If someone is in danger, call 911.
- Termination: the operator may disable the service for abuse (dial storms, spoofing) or if funding ends, with notice.
- Governing law and dispute resolution: counsel's call; seniors as a class deserve a plain-language, non-punitive clause.
- Open-source notice: the software is Apache-2.0 (pending), and the terms govern the hosted service, not the code.
- Changes: material changes trigger re-consent in the app (`consent_version`).

## Questions for counsel

1. Does the in-call announcement, combined with the far party staying on the line, satisfy the all-party-consent statutes in California (§ 632, § 632.7) and Washington (RCW 9.73.030(3)) when no recording is made and a machine performs the listening?
2. Is real-time transmission of the audio to Deepgram and of text to Anthropic a further interception or disclosure requiring separate analysis, or covered by the same consent?
3. Can the announcement be turned off for seniors in one-party states, given Kearney and the unknown location of the far party? The maintainer's assumption is no.
4. Does § 633.5 or any similar "recording to obtain evidence of a crime" exception help a senior who suspects a scam mid-call? The maintainer's assumption is that it is not something to rely on.
5. Is a raw recording of a template sentence a "voiceprint" or "biometric identifier" under BIPA or the Texas and Washington statutes?
6. What must the terms and the in-app copy say about the accuracy of the AI's guidance to limit negligence and consumer-protection exposure, and is an arbitration clause appropriate for a free service to seniors?
7. Does marketing the product as scam detection create an implied warranty, and what wording avoids it?
8. What entity should operate the service? A personal project today; a 501(c)(3) is the goal. Does the choice change the consent analysis or the liability exposure, and what insurance is needed?
9. Are there any state laws on "call monitoring services" or on assistive technology for seniors that add registration or disclosure requirements?
10. Guardian linking: does adding a family member who receives alerts about the senior's calls create any duty to the senior beyond the terms, and what should the senior's consent screen say about it?
11. Is the Firebase OTP SMS, sent when the user enters their own number, cleanly outside the TCPA?
12. Does anything in the design trigger state data-broker, data-privacy (CCPA/CPRA), or "sensitive data" rules given that the operator has under 100,000 users and no revenue? CPRA thresholds should exclude it; verify.
13. Retention: is 30 days for session metadata and 90 days for usage events defensible, and does the 1-year anonymised deletion record create any problem?
14. Should the operator obtain the far party's consent in writing in any scenario, for example when a guardian is a professional caregiver?

## Carrier matrix

Identical to the table in `docs/ARCHITECTURE.md`. Filled in during the one-day spike. Counsel needs it because "who ends the conference" and "does the far party hear a beep" bear on whether the far party could know they were being listened to before the announcement.

| Carrier | Phone | Merge offered | Seconds to Merge | Far party hears | Who ends the conference | Notes |
|---|---|---|---|---|---|---|
| Verizon | | | | | | |
| AT&T | | | | | | |
| T-Mobile | | | | | | |
| Consumer Cellular | | | | | | |
| Lively | | | | | | |
| MVNO (name) | | | | | | |
| Wi-Fi Calling (carrier) | | | | | | |
