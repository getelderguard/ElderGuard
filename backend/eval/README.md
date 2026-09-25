# Scorer evaluation

Offline evaluation of the live-call scoring pipeline: the rolling transcript window, the
regex trip-wire, the evidence gate, the adaptive cadence and the dial hysteresis in
`app/scoring/rolling.py`, driven by a scorer that is either the deterministic fake or the
real Anthropic scorer.

The question it answers is the one that decides whether ElderGuard is shippable: **how often
does STOP fire on a real doctor, a real bank, or a real grandchild, and how fast does it fire
on a scam?**

## The corpus

`fixtures/*.jsonl`, one transcript per line:

```json
{"id": "medicare_benefits-004", "label": "scam", "category": "medicare_benefits",
 "notes": "resistance=questioning subtle_open=True hung_up=False", "first_action_t": 71.3,
 "segments": [{"t": 0.0, "speaker": "senior", "text": "Hello?"}, ...]}
```

- `t` is seconds from call start. `first_action_t` (scam only) is when the caller first asks
  for money, access, a code, or silence; time-to-STOP is measured from there as well as from
  call start.
- 150 scam transcripts across 15 categories (Medicare, SSA suspension, IRS warrant,
  grandchild emergency, tech-support remote access, fake bank fraud desk, Amazon refund,
  utility shut-off, romance, lottery, pressure charity, crypto, jury duty, package fee,
  warranty upsell), 10 each.
- 160 benign transcripts across 16 categories, 10 each, including the hard negatives that
  share vocabulary with scams: a real bank fraud desk that never asks for a code, a pharmacy
  confirming a date of birth, a grandchild who genuinely needs money, a family argument about
  money, a support call the senior placed themselves, a legitimate refund.

The transcripts are fiction, composed by `corpus/generate.py` from per-category dialogue
banks in `corpus/scam_banks.py` and `corpus/benign_banks.py`. Every call samples its own
names, amounts, pretext lines, senior resistance (compliant, questioning, or resistant, some
of whom hang up), filler, stalls and pacing, so calls in a category share an arc but not a
script. About a third of scams open with a minute of harmless small talk before the pretext.

Two honesty notes about the corpus:

- The scam banks lean on the urgency and secrecy vocabulary real scammers use ("right now",
  "don't hang up", "don't tell anyone"). That is realistic, but it also happens to be what
  the fake scorer's regexes look for, so fake-scorer recall flatters the harness. It says
  nothing about the model.
- No scam or benign fixture was edited to dodge a specific score. Where a benign call trips
  the fake scorer (a pharmacy that mentions Medicare, a date of birth and the grandchildren
  in the same minute), it stays in the corpus, because that is exactly the call the real
  model has to get right.

### Adding fixtures

Hand-written transcripts are welcome and should go in a new file, for example
`fixtures/scam_handwritten.jsonl`, so regeneration does not overwrite them. Keep the shape
above, use `speaker` values `caller` and `senior`, and set `first_action_t` on scams.
Real call transcripts must never be added here: the product stores none, and this directory
is public.

To regenerate the composed corpus (deterministic for a seed):

```bash
cd backend
uv run python -m eval.corpus.generate --per-category 10 --seed 20260925
```

## Running

Fake scorer, whole corpus, about a second:

```bash
cd backend
uv run python eval/run.py            # table on stdout, eval/out/report.json
uv run python eval/run.py --gate     # exit 1 if a gate fails; this is what CI runs
uv run python eval/run.py --runs 3   # repeat with different shuffles, report variance
```

Real scorer (spends money; the cap stops the run when the estimate is exceeded):

```bash
cd backend
ANTHROPIC_API_KEY=... uv run python eval/run.py --scorer anthropic --limit 60 --max-cost-usd 2
ANTHROPIC_API_KEY=... uv run python eval/run.py --scorer anthropic --gate --runs 3
```

`--model` picks the Anthropic model (default `claude-sonnet-5`). Requests run four at a time.
The key is read from the environment only; the script refuses to run without it and never
prints it.

Each transcript is replayed against `RollingScorer` with a fake clock at the production
cadence constants (first 60 s every final, then 15 s listening / 5 s caution / 8 s stop,
4 s minimum gap, trip-wire override). Scorer latency is not simulated: virtual time only
advances with the transcript, so time-to-STOP here is a lower bound on what a live call sees.
Add roughly one scorer round-trip (1 to 2 s) for the real number.

## What the table means

| Row | Meaning |
|---|---|
| STOP false-positive rate | Benign calls where the tier reached STOP at any point. The product-killer metric. |
| CAUTION false-positive rate | Benign calls that reached CAUTION. A caution on a real bank call is tolerable; a pattern of them is not. |
| STOP recall | Scam calls that reached STOP. Some scams end with the senior hanging up before the ask completes, which counts as a miss. |
| time-to-STOP after first ask | Seconds from the caller's first concrete ask (money, access, code, silence) to STOP. This is the number that matters for a senior mid-call. |
| time-to-STOP from call start | The same, measured from the first word. Subtle scams with a small-talk opener push this up. |
| scorer calls per audio minute | Cost driver. The plan budgets 20 to 30 scores per 6-minute call, about 3.5 to 5 per minute. |
| estimated cost per 6-minute call | From `PRICE_TABLE` in `app/providers/metrics.py`. Zero for the fake. |

## Gates

`--gate` applies thresholds by scorer:

| Scorer | STOP FP | CAUTION FP | STOP recall | median time-to-STOP after first ask |
|---|---|---|---|---|
| `fake` | <= 1% | <= 15% | >= 80% | reported, not gated |
| `anthropic` | <= 1% | <= 15% | reported, not gated | <= 60 s |

The fake-scorer gate is a harness sanity check. The fake scorer is a regex over the transcript
window (`app/providers/fake.py`), so its numbers prove that the window, the trip-wire, the
evidence gate and the two-signal STOP rule behave, and that a change to `rolling.py` did not
quietly make STOP easier or harder to reach. They do not measure scam detection. The Anthropic
gate is the launch bar from the plan and runs on demand, with variance from `--runs 3`,
before any real phone is enrolled.

## Pipeline simulator

`simulate.py` runs the same scoring on what a speech-to-text provider actually hears, so
transcription errors are part of the measurement:

```bash
cd backend
uv run python eval/simulate.py --limit 5                           # fakes end to end, no keys
STT_API_KEY=... uv run python eval/simulate.py --transcriber deepgram --limit 3 --realtime
```

Text is synthesized (fake only until the M3 voice work lands, which is also when this becomes
meaningful), converted to 8 kHz mulaw through `app/telephony/codec.py`, pushed in 20 ms
frames like Twilio does, and the transcriber's finals are scored. With the fake synthesizer
the audio is silence and the fake transcriber echoes the fixture text, so today the simulator
proves the plumbing, not the word error rate.

## Current fake-scorer numbers

From `uv run python eval/run.py --gate` on the checked-in corpus:

- STOP false positives 0.6% (one pharmacy call that mentions Medicare, a date of birth and
  the grandchildren within one window; a regex cannot tell that apart from a scam).
- CAUTION false positives 8.8%, almost all the pharmacy category.
- STOP recall 92%. Romance scams are the weak category for the regex scorer (6 of 10), since
  they carry fewer of its keywords.
- Median time-to-STOP after the first ask 21 s, p90 70 s. About 5.5 scorer calls per
  audio minute.
