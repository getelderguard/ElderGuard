"""Compose the fixture corpus from the dialogue banks.

    cd backend && uv run python -m eval.corpus.generate [--per-category 10] [--seed 20260925]

Every call samples its own names, amounts, pretext lines, senior resistance, filler and
pacing, so calls in one category share an arc but not a script. Output is deterministic
for a given seed and is checked in under eval/fixtures/.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from eval.corpus import benign_banks, scam_banks
from eval.corpus.model import Beat, Scenario

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

SENIORS = [
    "Eleanor",
    "Dorothy",
    "Harold",
    "Walter",
    "Margaret",
    "Ruth",
    "Frank",
    "Betty",
    "Gloria",
    "Arthur",
    "Joan",
    "Leonard",
    "Shirley",
    "Norman",
    "Phyllis",
    "Ernest",
]
CALLERS = [
    "Kevin",
    "Priya",
    "David",
    "Marcus",
    "Linda",
    "Steven",
    "Angela",
    "Robert",
    "Nina",
    "Brian",
    "Carla",
    "Tom",
    "Jessica",
    "Raymond",
    "Monica",
    "Daniel",
]
GRANDKIDS = ["Tyler", "Emma", "Jake", "Sophie", "Brandon", "Olivia", "Ryan", "Chloe", "Matt"]
RELATIVES = ["Danny", "Lisa", "your brother", "Aunt Carol", "Mike", "Karen", "Uncle Ray"]
CITIES = [
    "El Paso",
    "Tucson",
    "Dayton",
    "Fresno",
    "Tampa",
    "Buffalo",
    "Reno",
    "Mobile",
    "Spokane",
    "Akron",
]
STORES = [
    "the drugstore",
    "the grocery store",
    "the big box store",
    "the gas station",
    "the pharmacy",
    "the dollar store",
]
STREETS = ["Maple Street", "Elm Avenue", "Oak Lane", "Third Street", "Willow Drive", "Cedar Court"]
DOCTORS = ["Patel", "Nguyen", "Okafor", "Brennan", "Schultz", "Alvarez"]
AMOUNTS_SCAM = [
    "four hundred dollars",
    "nine hundred and fifty dollars",
    "two thousand dollars",
    "fifteen hundred dollars",
    "three thousand dollars",
    "six hundred dollars",
    "eighteen hundred dollars",
    "twelve hundred dollars",
]
AMOUNTS_BENIGN = [
    "forty three dollars",
    "a hundred and twenty dollars",
    "three hundred dollars",
    "eighty six dollars",
    "six hundred dollars",
    "two hundred and fifty dollars",
    "nine hundred dollars",
    "thirty dollars",
]

SCAM_RAPPORT = [
    "Are you at home by yourself today, {senior}?",
    "Do you have a car, or does someone drive you?",
    "And you're still at the same address on {street}, correct?",
    "How old are you now, {senior}, if you don't mind my asking?",
    "Is your husband home, or is it just you?",
    "Do you do your banking online or in person?",
]
SCAM_WALKTHROUGH = [
    "Okay, which store is closest to you? Good. Take the phone with you in the car, we need to go right now.",
    "When you get to the register, ask for the gift cards in the amounts I told you. Don't tell them what they're for.",
    "If the cashier asks questions, just tell them it's a birthday gift. Don't tell them anything else.",
    "Once you have them, scratch off the silver strip on the back and read me the numbers slowly.",
    "Are you in the car yet? Keep me on speaker. Don't hang up.",
    "Okay, I'm waiting. Let me know when you're at the counter. Don't hang up on me.",
    "I'll stay on the line the whole time so nothing goes wrong. Just don't tell anyone what you're doing.",
    "Hurry, please. This has to be done immediately or the whole thing falls through.",
]
BENIGN_SMALL_TALK = [
    (
        "How are you holding up with this heat?",
        "Oh, I keep the fan on and don't go out until evening.",
    ),
    ("How's the hip doing?", "Better. The therapy helps, but the stairs are still slow."),
    (
        "Did your daughter make it up for the holiday?",
        "She did, with the kids. The house was a zoo.",
    ),
    ("How's the garden this year?", "The tomatoes are late but the beans went crazy."),
    ("Is the cat still bossing you around?", "Every morning at five. Like clockwork."),
    ("Did you get any of that rain last night?", "Just a little. The gutters are still holding."),
    ("Are you still doing the water aerobics?", "Tuesdays and Thursdays. My friend Marge drives."),
    (
        "How was the birthday party?",
        "Loud. Eleven little ones and a piñata. I was in bed by eight.",
    ),
    (
        "Did the furnace get fixed?",
        "The young man came out Tuesday. It was a sensor, thirty dollars.",
    ),
    (
        "Have you heard from your son lately?",
        "He calls Sundays. He's in Denver now, with the airline.",
    ),
    (
        "How's the new hearing aid working out?",
        "Better, once I figured out the little app. My granddaughter set it up.",
    ),
    ("Did you watch the game last night?", "I fell asleep in the third quarter. Did they win?"),
    ("Are you going to the senior center lunch this week?", "Wednesday is meatloaf, so yes."),
    (
        "How's Harold's brother doing after the surgery?",
        "Home now. Grumpy as ever, so he must be fine.",
    ),
    ("Did you get the pictures I sent?", "I did. The baby has your father's ears, poor thing."),
    (
        "Is your knee any better?",
        "Some days. The doctor wants to do the injection again in the spring.",
    ),
]
BENIGN_TANGENTS = [
    "Oh, before I forget. My neighbor's boy is selling his old car and I told him I'd ask around. Do you know anyone?",
    "Hold on, let me turn the stove down. Okay, I'm back. Where were we?",
    "You know, I was just telling my sister about you the other day. She remembers when you were little.",
    "Sorry, I had to sit down. My legs aren't what they were. Go on.",
    "I got a letter from the county about the property taxes. I'll have my son look at it when he's here.",
    "The mail carrier just came. Hold on. Alright, it's just the flyer from the grocery store.",
]
SCAM_STALL = [
    "Hold on, let me find my glasses. Where did I put them.",
    "Wait, wait, I need to get my purse. It's in the other room.",
    "Let me get a pen. Okay. Say the number again?",
    "Can you say that slower? I'm writing it down.",
    "My hands are shaking. Give me a second.",
]
SCAM_HOLD = [
    (
        "I'm going to put you on a brief hold while I pull up your file. Please don't hang up.",
        "Alright.",
        "Okay, I'm back. Thank you for holding. Now, where were we.",
        "You were saying about my file.",
    ),
    (
        "Bear with me one moment, the system is slow today.",
        "Okay.",
        "There we go. I have it in front of me now.",
        "Alright.",
    ),
    (
        "Let me get my supervisor on the line. Stay right there.",
        "I'm here.",
        "Okay, my supervisor has approved it. Let's continue.",
        "Go on.",
    ),
]
PERSONAL = {
    "grandchild_emergency": {
        "preamble": [
            (
                "Grandma, can you hear me okay? The line is bad in here.",
                "I can hear you. You sound stuffy.",
            ),
            ("Are you home alone right now?", "Yes, just me and the cat."),
            ("I only get one call, so please just listen.", "Okay, okay. I'm listening."),
        ],
        "rapport": [
            "Grandma, are you still there? Please, I don't have much time.",
            "I know it's a lot. I'll pay you back from my summer job, I promise.",
            "Please don't cry, Grandma. I'm okay, I just need to get out of here.",
            "The lawyer says it's routine, it happens all the time, but it has to be right now.",
        ],
        "walkthrough": [
            "The lawyer will text you the address of the store. Just get the gift cards and read him the numbers.",
            "A courier is going to come to the door for the cash. Just hand him the envelope, don't tell him anything.",
            "Please don't hang up and call Mom. Promise me. Don't tell her.",
            "Hurry, Grandma. They said if it's not paid within the hour they move me.",
        ],
    },
    "romance_money": {
        "preamble": [
            ("Did you get the flowers I sent?", "I did, they're beautiful."),
            ("How was your day, my darling?", "Quiet. I went to the market and fed the birds."),
            ("I was looking at your picture all through my shift.", "Oh, stop. You're too much."),
        ],
        "rapport": [
            "I've never felt this way about anyone, {senior}.",
            "I'm going to lose everything if this doesn't go through tonight.",
            "Do you trust me? Then please, just this once.",
            "Nobody has ever been there for me the way you are.",
        ],
        "walkthrough": [
            "Go to the Western Union counter at the grocery store. The name is on the text I sent you.",
            "When they ask what it's for, say it's for family. Don't tell them it's for me, they ask too many questions.",
            "Send me a picture of the receipt as soon as it's done, my love. Do it right now, before the counter closes.",
            "Please don't hang up on me. I need to hear your voice while I wait.",
        ],
    },
}
SCAM_PREAMBLE = [
    ("Before we begin, how are you doing today, {senior}?", "Oh, I'm alright. Just getting old."),
    (
        "I hope I'm not calling too early. Have you had your breakfast?",
        "I've had my coffee, that's enough.",
    ),
    ("It's a beautiful day out there, isn't it?", "It is. I was going to sit on the porch."),
    ("This is just a routine courtesy call, nothing to worry about.", "Alright."),
    (
        "I'll be quick, I know you're busy. Can you confirm you're still on {street}?",
        "Yes, still here. Forty years.",
    ),
]
SCAM_CLOSERS = [
    "Okay, I'll stay on the line. Go ahead and get your keys.",
    "Good. I'll call you back in twenty minutes to get the numbers. Don't talk to anyone.",
    "Thank you, {senior}. You're doing the right thing.",
]
SENIOR_HANGUP = [
    "No. I'm hanging up now.",
    "I'm going to call the real number. Goodbye.",
    "Goodbye. Don't call here again.",
]


class Call:
    def __init__(self, rng: random.Random, words_per_s: float) -> None:
        self.rng = rng
        self.wps = words_per_s
        self.t = 0.0
        self.segments: list[dict] = []

    def say(self, speaker: str, text: str) -> None:
        words = max(1, len(text.split()))
        self.segments.append({"t": round(self.t, 1), "speaker": speaker, "text": text})
        duration = words / self.wps + self.rng.uniform(0.2, 0.9)
        self.t += duration + self.rng.uniform(0.6, 2.4)


def _fill(text: str, ctx: dict[str, str]) -> str:
    return text.format(**ctx)


def _context(rng: random.Random, label: str) -> dict[str, str]:
    return {
        "senior": rng.choice(SENIORS),
        "caller": rng.choice(CALLERS),
        "grandkid": rng.choice(GRANDKIDS),
        "relative": rng.choice(RELATIVES),
        "city": rng.choice(CITIES),
        "store": rng.choice(STORES),
        "street": rng.choice(STREETS),
        "doctor": rng.choice(DOCTORS),
        "amount": rng.choice(AMOUNTS_SCAM if label == "scam" else AMOUNTS_BENIGN),
        "last4": str(rng.randint(1000, 9999)),
        "badge": str(rng.randint(10000, 99999)),
    }


def _senior_reply(rng: random.Random, beat: Beat, resistance: str, ctx: dict[str, str]) -> str:
    if beat.senior:
        return _fill(rng.choice(beat.senior), ctx)
    pool = {
        "compliant": scam_banks.COMPLIANT,
        "questioning": scam_banks.QUESTIONING,
        "resistant": scam_banks.RESISTANT if beat.action else scam_banks.QUESTIONING,
    }[resistance]
    return _fill(rng.choice(pool), ctx)


def build_scam(sc: Scenario, rng: random.Random, n: int) -> dict:
    ctx = _context(rng, "scam")
    resistance = rng.choices(["compliant", "questioning", "resistant"], [45, 35, 20])[0]
    subtle = rng.random() < 0.3
    call = Call(rng, rng.uniform(1.9, 2.6))
    personal = PERSONAL.get(sc.category)
    preamble = personal["preamble"] if personal else SCAM_PREAMBLE
    rapport = personal["rapport"] if personal else SCAM_RAPPORT
    walkthrough = personal["walkthrough"] if personal else SCAM_WALKTHROUGH

    call.say("senior", _fill(rng.choice(sc.senior_opener), ctx))
    call.say("caller", _fill(rng.choice(sc.openers), ctx))
    if personal:
        call.say(
            "senior",
            _fill(
                rng.choice(
                    ["Who is this?", "{grandkid}? Is that you?", "Oh, hello.", "What's wrong?"]
                ),
                ctx,
            ),
        )
    else:
        call.say(
            "senior",
            _fill(
                rng.choice(
                    ["Yes, this is {senior}.", "Yes?", "Speaking. What's this about?", "Who?"]
                ),
                ctx,
            ),
        )

    if subtle:
        for q, a in rng.sample(preamble, k=min(len(preamble), rng.randint(2, 4))):
            call.say("caller", _fill(q, ctx))
            call.say("senior", _fill(a, ctx))

    beats = [b for b in sc.beats if not b.optional or rng.random() < 0.65]
    hung_up = False
    first_action_t: float | None = None
    for i, beat in enumerate(beats):
        if beat.action and first_action_t is None:
            first_action_t = round(call.t, 1)
        call.say("caller", _fill(rng.choice(beat.caller), ctx))
        if rng.random() < 0.25:
            call.say("senior", rng.choice(scam_banks.FILLER_SENIOR))
            call.say("caller", _fill(rng.choice(rapport), ctx))
        reply = _senior_reply(rng, beat, resistance, ctx)
        call.say("senior", reply)
        pushback = reply in scam_banks.RESISTANT or reply in scam_banks.QUESTIONING
        if pushback and rng.random() < 0.85:
            call.say("caller", _fill(rng.choice(scam_banks.PUSHBACK), ctx))
            if resistance == "resistant" and beat.action and rng.random() < 0.5:
                call.say("senior", rng.choice(SENIOR_HANGUP))
                hung_up = True
                break
            call.say(
                "senior", _fill(rng.choice(scam_banks.COMPLIANT + scam_banks.FILLER_SENIOR), ctx)
            )
        if beat.action and not hung_up and rng.random() < 0.7:
            for line in rng.sample(walkthrough, k=rng.randint(1, 3)):
                call.say("caller", _fill(line, ctx))
                call.say(
                    "senior",
                    rng.choice(scam_banks.FILLER_SENIOR + scam_banks.COMPLIANT + SCAM_STALL),
                )
        if i == 0 and not personal and rng.random() < 0.4:
            hold, ack, back, ack2 = rng.choice(SCAM_HOLD)
            call.say("caller", hold)
            call.say("senior", ack)
            call.say("caller", back)
            call.say("senior", ack2)

    target = rng.uniform(120, 240)
    while not hung_up and call.t < target:
        line = rng.choice(walkthrough + scam_banks.PUSHBACK + rapport)
        call.say("caller", _fill(line, ctx))
        call.say(
            "senior",
            _fill(rng.choice(scam_banks.FILLER_SENIOR + SCAM_STALL + scam_banks.QUESTIONING), ctx),
        )

    if not hung_up:
        call.say("caller", _fill(rng.choice(SCAM_CLOSERS), ctx))
        call.say("senior", rng.choice(scam_banks.COMPLIANT + scam_banks.FILLER_SENIOR))

    return {
        "id": f"{sc.category}-{n:03d}",
        "label": "scam",
        "category": sc.category,
        "notes": f"resistance={resistance} subtle_open={subtle} hung_up={hung_up}",
        "first_action_t": first_action_t,
        "segments": call.segments,
    }


def build_benign(sc: Scenario, rng: random.Random, n: int) -> dict:
    ctx = _context(rng, "benign")
    call = Call(rng, rng.uniform(1.9, 2.6))
    track = rng.randrange(len(sc.senior_opener)) if sc.aligned else None

    def pick(options: list[str]) -> str:
        if track is None or not options:
            return rng.choice(options)
        return options[track % len(options)]

    call.say("senior", _fill(pick(sc.senior_opener), ctx))
    call.say("caller", _fill(rng.choice(sc.openers), ctx))
    if not sc.senior_opener or sc.senior_opener[0] == "Hello?":
        call.say(
            "senior", rng.choice(["Yes, this is she.", "Yes, speaking.", "That's me.", "Yes?"])
        )
    if rng.random() < 0.7:
        for q, a in rng.sample(BENIGN_SMALL_TALK, k=rng.randint(1, 3)):
            call.say("caller", q)
            call.say("senior", a)
    for beat in sc.beats:
        if beat.optional and rng.random() < 0.4:
            continue
        call.say("caller", _fill(pick(beat.caller), ctx))
        if rng.random() < 0.2:
            call.say("senior", rng.choice(scam_banks.FILLER_SENIOR))
            call.say("caller", rng.choice(["Sure.", "Of course.", "No problem, take your time."]))
        call.say(
            "senior",
            _fill(pick(beat.senior) if beat.senior else rng.choice(benign_banks.SENIOR_OK), ctx),
        )
        if rng.random() < 0.3:
            call.say("senior", rng.choice(BENIGN_TANGENTS))
            call.say(
                "caller",
                rng.choice(
                    ["Of course.", "No rush.", "Ha, that's alright.", "Sure, take your time."]
                ),
            )
    used = set()
    target = rng.uniform(120, 240)
    while call.t < target and len(used) < len(BENIGN_SMALL_TALK):
        q, a = rng.choice(BENIGN_SMALL_TALK)
        if q in used:
            continue
        used.add(q)
        call.say("caller", q)
        call.say("senior", a)
    if sc.closers:
        call.say("caller", _fill(rng.choice(sc.closers), ctx))
        call.say("senior", rng.choice(["Bye now.", "Goodbye.", "Thank you, bye.", "Take care."]))
    return {
        "id": f"{sc.category}-{n:03d}",
        "label": "benign",
        "category": sc.category,
        "notes": "hard_negative" if sc.category in HARD_NEGATIVES else "ordinary",
        "first_action_t": None,
        "segments": call.segments,
    }


HARD_NEGATIVES = {
    "real_bank_fraud_desk",
    "pharmacy_dob_confirmation",
    "grandchild_genuinely_asking_for_money",
    "family_money_argument",
    "tech_support_senior_initiated",
    "refund_legit",
    "utility_billing_legit",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260925)
    args = ap.parse_args()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    total = {"scam": 0, "benign": 0}
    for sc in scam_banks.SCAM_SCENARIOS + benign_banks.BENIGN_SCENARIOS:
        builder = build_scam if sc.label == "scam" else build_benign
        path = FIXTURES / f"{sc.label}_{sc.category}.jsonl"
        with path.open("w") as f:
            for n in range(1, args.per_category + 1):
                f.write(json.dumps(builder(sc, rng, n)) + "\n")
                total[sc.label] += 1
    print(f"wrote {total['scam']} scam and {total['benign']} benign transcripts to {FIXTURES}")


if __name__ == "__main__":
    main()
