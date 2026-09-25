"""Dialogue banks for benign scenarios, including hard negatives that share vocabulary with
scams (a real bank fraud desk, a pharmacy confirming a birth date, a grandchild who really
does need money). Fiction written for testing."""

from __future__ import annotations

from eval.corpus.model import Beat, Scenario


def _s(*variants: str) -> list[str]:
    return list(variants)


SENIOR_OK = [
    "Alright.",
    "Okay, thank you.",
    "That's fine.",
    "Sure, go ahead.",
    "Yes, that works.",
    "Mm-hmm, I understand.",
]

REAL_BANK = Scenario(
    category="real_bank_fraud_desk",
    label="benign",
    openers=_s(
        "Hi, this is {caller} calling from the fraud monitoring team at your bank. I'm calling about the debit card ending in {last4}.",
        "Good morning, this is {caller} with the card services department. We noticed an unusual transaction on the card ending in {last4}.",
        "Hello {senior}, {caller} from the bank's fraud desk. This is just a courtesy call about a purchase we flagged.",
    ),
    beats=[
        Beat(
            _s(
                "I won't ask you for your card number or any codes. I just need a yes or no on a couple of purchases.",
                "For your security I'll never ask for your PIN or a passcode. I'll just describe the charges and you tell me if they're yours.",
            ),
            senior=_s("Alright, go ahead.", "Okay. I appreciate that.", "Fine, what are they?"),
        ),
        Beat(
            _s(
                "There's a charge of {amount} at a hardware store in {city} this morning. Does that sound like you?",
                "We see a {amount} purchase at a gas station in {city} at about ten o'clock. Was that you?",
            ),
            senior=_s(
                "Yes, that was me. I bought a new hose.",
                "Yes, I filled up on the way to my sister's.",
                "No, I don't think so. I haven't been to {city}.",
                "Hmm, {amount}? Let me think. Oh yes, that was the garden center.",
            ),
        ),
        Beat(
            _s(
                "Okay, I've noted that. There's also a small online charge of four dollars and ninety nine cents. Recognize that one?",
                "Thank you. And one more, a subscription renewal for a streaming service yesterday?",
            ),
            senior=_s(
                "Oh, that's the crossword app my granddaughter set up.",
                "Yes, that's the television thing.",
                "That one I don't recognize, no.",
            ),
        ),
        Beat(
            _s(
                "Perfect. I've cleared the alert on your card. You don't need to do anything else.",
                "Since one charge wasn't yours, I'm going to cancel this card and mail a new one. It arrives in five to seven business days.",
                "You're all set. If you ever want to confirm a call like this, hang up and call the number on the back of your card.",
            ),
            senior=_s(
                "Thank you, that's a relief.", "Okay. I'll do that.", "Thank you for checking."
            ),
        ),
    ],
    closers=_s(
        "You're welcome. Have a good day, {senior}.",
        "Thanks for your time. Goodbye.",
    ),
)

PHARMACY = Scenario(
    category="pharmacy_dob_confirmation",
    label="benign",
    openers=_s(
        "Hi, this is {caller} from the pharmacy on {street}. I'm calling about a prescription for {senior}.",
        "Hello, this is the pharmacy. Is {senior} available? We have a refill question.",
        "Good afternoon, {caller} at the pharmacy. Your doctor sent over a new prescription and I have a quick question.",
    ),
    beats=[
        Beat(
            _s(
                "Before I go into the medication, can you confirm your date of birth for me?",
                "I just need to verify your date of birth so I'm looking at the right profile.",
            ),
            senior=_s(
                "It's the fourth of March, nineteen forty two.",
                "September twelfth, forty five.",
                "June second, nineteen thirty nine.",
            ),
        ),
        Beat(
            _s(
                "Thank you. The blood pressure medication your doctor sent is a different strength than last time. Did she mention a change?",
                "Your insurance needs a prior authorization for the new inhaler. We've faxed the doctor, it may take a couple of days.",
                "Your Medicare Part D plan changed the copay on the cholesterol pill. It's going to be twelve dollars instead of four this time.",
            ),
            senior=_s(
                "She did say she was raising it, yes.",
                "Oh, alright. I still have some left so that's fine.",
                "Twelve dollars? Well, I suppose that's alright.",
                "Is there a generic that's cheaper?",
            ),
        ),
        Beat(
            _s(
                "I can have it ready by four o'clock today, or we can deliver tomorrow morning.",
                "There's a generic that would bring it down to six dollars. Want me to switch it?",
                "I'll put it through. Would you like a text when it's ready?",
            ),
            senior=_s(
                "Tomorrow morning is better, my son drives me.",
                "Yes please, the cheaper one.",
                "A text is fine. Or just call, I don't always see the texts.",
            ),
        ),
        Beat(
            _s(
                "Will do. Anything else you need refilled while I have you?",
                "Got it. Is there anything else I can help with today?",
            ),
            senior=_s(
                "No, that's everything. Thank you dear.",
                "Actually, could you check if my eye drops are due?",
                "No, that's all.",
            ),
            optional=True,
        ),
    ],
    closers=_s("Alright, have a good one, {senior}.", "Take care now.", "See you tomorrow."),
)

DOCTOR = Scenario(
    category="doctor_office_scheduling",
    label="benign",
    openers=_s(
        "Hi, this is {caller} from Dr. {doctor}'s office. Is this {senior}?",
        "Hello {senior}, it's {caller} at the clinic. I'm calling about your appointment.",
        "Good morning, this is the cardiology office calling for {senior}.",
    ),
    beats=[
        Beat(
            _s(
                "Dr. {doctor} had a scheduling change and we need to move your Thursday appointment. Would next Tuesday at ten work?",
                "We have your follow-up down for the fourteenth at two. I just wanted to confirm you're still able to make it.",
                "Your lab results came back and the doctor would like to see you a little sooner. Can you come in Monday?",
            ),
            senior=_s(
                "Tuesday at ten is fine. Let me write that down.",
                "Yes, I'll be there. My daughter is driving me.",
                "Monday? Is something wrong?",
                "Can we do the afternoon? I have physical therapy in the morning.",
            ),
        ),
        Beat(
            _s(
                "Nothing alarming, she just wants to adjust one of your medications and talk it through in person.",
                "Perfect. Please bring your medication list and your insurance card.",
                "Afternoon works. How about one thirty?",
            ),
            senior=_s(
                "Alright, one thirty then.",
                "I'll bring the list. Same parking lot?",
                "Okay, that puts my mind at ease.",
            ),
        ),
        Beat(
            _s(
                "Same building, second floor. And you'll get a reminder call the day before.",
                "Yes, same place. Do you need the address again?",
            ),
            senior=_s("No, I know where it is.", "Thank you, that's helpful."),
            optional=True,
        ),
    ],
    closers=_s("Great, we'll see you then.", "Take care, {senior}.", "Bye now."),
)

GRANDCHILD_REAL = Scenario(
    category="grandchild_genuinely_asking_for_money",
    label="benign",
    openers=_s(
        "Hi Grandma, it's {grandkid}. Do you have a minute?",
        "Hey Grandpa, it's {grandkid}. How are you feeling today?",
        "Hi Nana, it's me, {grandkid}. Is this a bad time?",
    ),
    senior_opener=_s(
        "Hello?",
        "Oh, hi sweetheart!",
        "{grandkid}! What a nice surprise.",
    ),
    beats=[
        Beat(
            _s(
                "So, I feel weird asking. My car needs a new alternator and it's {amount}. I get paid on the fifteenth but the shop wants it now.",
                "I'm a little short on rent this month because my hours got cut. I was wondering if I could borrow {amount} until my next check.",
                "My tuition payment is due Friday and the loan got delayed. Would you be able to lend me {amount}? I'll pay it back in June.",
            ),
            senior=_s(
                "Oh honey, of course. Did you talk to your mother about it?",
                "How much again? {amount}? Let me look at my checkbook.",
                "You know I'd rather you ask me than put it on a credit card.",
                "Is everything else okay? You sound tired.",
            ),
        ),
        Beat(
            _s(
                "I told Mom, she said to ask you since she just paid the roof guy. I feel bad though.",
                "Yeah, I'm okay, just stressed. I can come by Sunday and mow the lawn to make up for it.",
                "I already talked to Dad, he said it's fine but he's tapped out until payday.",
            ),
            senior=_s(
                "Don't feel bad. That's what grandmothers are for.",
                "Sunday would be lovely. I'll make the chicken you like.",
                "Alright. I'll write you a check, or I can do the bank transfer thing your cousin set up.",
            ),
        ),
        Beat(
            _s(
                "A check is perfect, I can pick it up Sunday. Thank you so much, Grandma.",
                "Either is fine. Honestly a check is easier, I'll deposit it on my phone.",
                "You don't have to rush, I can wait until Sunday. I love you.",
            ),
            senior=_s(
                "I love you too. Drive safe.",
                "Okay. And bring your laundry, I know you.",
                "See you Sunday, sweetheart.",
            ),
        ),
    ],
    closers=_s("Bye Grandma.", "Talk soon. Bye.", "Okay, bye, love you."),
)

CHARITY_LEGIT = Scenario(
    category="charity_legit_no_pressure",
    label="benign",
    openers=_s(
        "Hi {senior}, this is {caller} from the public library foundation. You've supported us before and I wanted to say thank you.",
        "Hello, this is {caller} calling from the food bank. I'm one of the volunteers.",
        "Good evening, {caller} with the animal shelter. Is this a good time?",
    ),
    beats=[
        Beat(
            _s(
                "We're doing our fall drive and I wanted to let you know. There's absolutely no obligation.",
                "Last year's gift helped us serve about two hundred more families. We're hoping to do the same this year.",
            ),
            senior=_s(
                "That's nice to hear. I do like the library.",
                "Oh, I remember. How's the new building coming along?",
                "I'm on a fixed income but I try to give a little.",
            ),
        ),
        Beat(
            _s(
                "Any amount is wonderful. If you'd like, I can mail you an envelope, or you can give on the website whenever you want.",
                "Whatever's comfortable. We can send a reply card in the mail so you don't have to do anything over the phone.",
            ),
            senior=_s(
                "Mail me the envelope, that's easiest.",
                "I'll send a check like last year.",
                "Let me think about it. Send the card.",
            ),
        ),
        Beat(
            _s(
                "Will do. And thank you again, it really does make a difference.",
                "Perfect. I'll get that out this week. Thanks so much for your time.",
            ),
            senior=SENIOR_OK,
            optional=True,
        ),
    ],
    closers=_s("Have a lovely evening.", "Take care, {senior}.", "Goodbye now."),
)

INSURANCE = Scenario(
    category="insurance_broker",
    label="benign",
    openers=_s(
        "Hi {senior}, it's {caller}, your insurance agent. Do you have a few minutes to go over your renewal?",
        "Hello, this is {caller} from the insurance office on {street}. I'm calling about your homeowner's policy.",
        "Hi, {caller} here from the agency. Your auto renewal came across my desk and I had a couple of notes.",
    ),
    beats=[
        Beat(
            _s(
                "Your premium went up about eight percent this year, which is what we're seeing across the board.",
                "The renewal is {amount} for the year. I found a discount for the new roof that brings it down a bit.",
                "Your car is getting older, so we could drop the collision coverage and save you about twenty dollars a month.",
            ),
            senior=_s(
                "Eight percent? Everything's going up.",
                "The roof was two years ago, does that still count?",
                "I'd rather keep the collision. I hit a deer once.",
            ),
        ),
        Beat(
            _s(
                "It does. I've applied it. I'll mail you the updated declarations page to look over.",
                "Completely understand. We'll leave it as is.",
                "I know. If you want, I can shop it with two other carriers and call you back next week.",
            ),
            senior=_s(
                "Please do shop it.",
                "Mail it, I'll look with my son.",
                "Alright, leave it the way it is.",
            ),
        ),
        Beat(
            _s(
                "Will do. Nothing to sign or pay today, the renewal just goes through automatically like before.",
                "Sounds good. Same auto-pay as always, nothing changes on your end.",
            ),
            senior=SENIOR_OK,
        ),
    ],
    closers=_s("Talk to you next week.", "Take care, {senior}.", "Thanks for your time."),
)

FAMILY_ARGUMENT = Scenario(
    category="family_money_argument",
    label="benign",
    openers=_s(
        "Mom, it's {caller}. Did you send {relative} money again?",
        "Hi Mom. Listen, I talked to {relative} and I'm a little upset.",
        "Mom, we need to talk about the money thing with {relative}.",
    ),
    senior_opener=_s("Hello?", "Hi honey.", "Oh, it's you. What's wrong?"),
    beats=[
        Beat(
            _s(
                "He said you gave him {amount} for his truck. That's the third time this year.",
                "You can't keep bailing her out, Mom. She's forty years old.",
                "I'm not mad at you, I'm mad at him. But you have to stop.",
            ),
            senior=_s(
                "He's my son, {caller}. What was I supposed to do?",
                "It's my money. I can do what I want with it.",
                "She was crying on the phone. I couldn't say no.",
                "Don't take that tone with me.",
            ),
        ),
        Beat(
            _s(
                "I know. I'm worried about you, that's all. Your savings has to last.",
                "You're right, it's your money. I just don't want you eating beans in December because he needed rims.",
                "Okay. Okay. I'm sorry. Can we at least agree you'll tell me before the next time?",
            ),
            senior=_s(
                "I have enough. Your father left me fine.",
                "Fine. I'll tell you. But I'm not promising I won't help him.",
                "I know you worry. I'm alright.",
            ),
        ),
        Beat(
            _s(
                "That's fair. Do you want to come for dinner Sunday? The kids miss you.",
                "Alright. I love you. Are you still coming Saturday?",
            ),
            senior=_s(
                "I'd like that. I'll bring the pie.",
                "Yes, I'll be there. Tell the kids I said hi.",
            ),
        ),
    ],
    closers=_s("Okay Mom. Love you.", "Bye Mom.", "See you Sunday."),
)

CHURCH = Scenario(
    category="church_friend",
    label="benign",
    openers=_s(
        "{senior}, it's {caller} from church. Did I catch you at a bad time?",
        "Hi {senior}, {caller} here. I missed you Sunday, is everything alright?",
        "Hello dear, it's {caller}. I'm calling about the potluck.",
    ),
    senior_opener=_s("Hello?", "Oh hi {caller}!", "Hello, who's this? Oh, {caller}!"),
    beats=[
        Beat(
            _s(
                "I'm doing my ham for the potluck and I wondered if you'd bring your bean salad. Everybody asks for it.",
                "I was just checking on you. Pastor said you'd been under the weather.",
                "We're putting together a card for {relative}, she's in the hospital again. Do you want me to sign your name?",
            ),
            senior=_s(
                "Of course I'll bring it. I'll need to get the beans.",
                "Oh I'm fine, just a cold. It's kind of you to check.",
                "Please do. What happened this time?",
            ),
        ),
        Beat(
            _s(
                "Her hip again. They think she'll be home by the weekend.",
                "Well, if you need anything from the store, I'm going Thursday.",
                "Wonderful. And can you make the big bowl this time? Last time it was gone in ten minutes.",
            ),
            senior=_s(
                "I'll make a double batch.",
                "Actually, could you pick up some cough drops?",
                "Poor thing. I'll call her tomorrow.",
            ),
        ),
        Beat(
            _s(
                "Sure thing. Alright, I'll let you go. See you Sunday?",
                "Okay dear. Take care of yourself.",
            ),
            senior=_s("See you Sunday.", "Thanks for calling, {caller}."),
        ),
    ],
    closers=_s("Bye now.", "Bye-bye.", "Take care."),
)

UTILITY_LEGIT = Scenario(
    category="utility_billing_legit",
    label="benign",
    openers=_s(
        "Hello, this is {caller} from the water department. I'm calling about the account at {street}.",
        "Hi, this is the electric company calling for {senior} regarding a scheduled maintenance.",
        "Good morning, {caller} with the gas utility. This is a courtesy call, nothing's wrong.",
    ),
    beats=[
        Beat(
            _s(
                "We'll be replacing meters on your street next Wednesday. Your water will be off for about an hour in the morning.",
                "There's a planned power outage in your area Tuesday from nine to eleven for line work.",
                "Your usage was quite a bit higher last month. We just want to make sure you don't have a leak.",
            ),
            senior=_s(
                "Alright. Do I need to be home?",
                "Nine to eleven? I'll make my coffee early.",
                "Higher? I did water the garden more with the heat.",
            ),
        ),
        Beat(
            _s(
                "No need. The crew works from the street. We'll leave a door hanger.",
                "That's probably it. If you see any damp spots in the basement, give us a call.",
                "You don't have to do anything. There's no charge and no change to your bill.",
            ),
            senior=SENIOR_OK,
        ),
        Beat(
            _s(
                "If you have any questions, the number on your bill goes right to us.",
                "That's all I had. Have a good day.",
            ),
            senior=_s("Thank you for letting me know.", "Alright, thanks."),
            optional=True,
        ),
    ],
    closers=_s("Goodbye.", "Take care."),
)

CONTRACTOR = Scenario(
    category="contractor_quote",
    label="benign",
    openers=_s(
        "Hi {senior}, it's {caller}, the plumber. I've got that estimate for the water heater.",
        "Hello, this is {caller} from the roofing company. I came by last week to look at the gutters.",
        "Hey {senior}, {caller} here. I wanted to go over the quote for the bathroom grab bars.",
    ),
    beats=[
        Beat(
            _s(
                "For the new water heater, installed and hauling away the old one, it comes to {amount}.",
                "The gutter repair is {amount}. If you want the guards added it's another four hundred.",
                "Two grab bars and the raised toilet seat, parts and labor, {amount}.",
            ),
            senior=_s(
                "{amount}. Hmm. That's more than I expected.",
                "Does that include the tax?",
                "My neighbor said hers was less.",
                "That sounds fair. When could you do it?",
            ),
        ),
        Beat(
            _s(
                "It does include tax. I can do it next Thursday if that works.",
                "I can knock a little off if you're fine with the standard model instead of the tankless.",
                "Hers might have been a smaller unit. But I'm happy to itemize it for you so you can compare.",
            ),
            senior=_s(
                "The standard one is fine.",
                "Thursday works. My son will be here.",
                "Yes, mail me the itemized one and I'll look it over.",
            ),
        ),
        Beat(
            _s(
                "Great. No deposit needed. You can pay when the job's done, check is fine.",
                "I'll email the itemized quote and you can take your time.",
            ),
            senior=SENIOR_OK,
        ),
    ],
    closers=_s("See you Thursday.", "Thanks {senior}, talk soon.", "Bye now."),
)

NEIGHBOR = Scenario(
    category="neighbor_chat",
    label="benign",
    openers=_s(
        "Hi {senior}, it's {caller} from next door. Did you get your power back?",
        "{senior}, it's {caller} across the street. I've got your mail, it came to me by mistake.",
        "Hey there, it's {caller}. I saw a truck outside your place, everything okay?",
    ),
    senior_opener=_s("Hello?", "Oh hi {caller}.", "{caller}! Hello."),
    beats=[
        Beat(
            _s(
                "The whole block was out for two hours. I kept thinking about your freezer.",
                "It's a big envelope from the county. I'll bring it over.",
                "Oh good. I was going to say, if you ever need a ride to the store, I go on Saturdays.",
            ),
            senior=_s(
                "It came back about noon. Nothing spoiled.",
                "Oh, that's probably the property tax thing. Thank you.",
                "That was just the furnace man. Annual checkup.",
            ),
        ),
        Beat(
            _s(
                "Glad to hear it. Say, are you going to the block party Saturday?",
                "I'll bring it after lunch. Do you need anything from the store?",
                "Oh good. Well I'll let you go, just wanted to check.",
            ),
            senior=_s(
                "I'll try. My knee's been acting up.",
                "Maybe some milk if you're going anyway.",
                "Thanks for checking, {caller}. You're a good neighbor.",
            ),
        ),
    ],
    closers=_s("Okay, take care.", "See you later.", "Bye!"),
)

TECH_SENIOR_INITIATED = Scenario(
    category="tech_support_senior_initiated",
    label="benign",
    aligned=True,
    openers=_s(
        "Thank you for calling support, this is {caller}. How can I help you today?",
        "Hi, you've reached the internet provider help desk, my name is {caller}. What's going on?",
        "Support line, this is {caller}. Can I get the name on the account?",
    ),
    senior_opener=_s(
        "Hello, yes, I'm calling because my email stopped working.",
        "Hi. My internet light is blinking red and I can't get online.",
        "Yes, hello. My tablet keeps asking for a password and I don't know it.",
    ),
    beats=[
        Beat(
            _s(
                "I can help with that. Is the email giving you an error, or just not loading?",
                "Sorry to hear that. Let's start with the basics, is the router plugged in and are any lights on?",
                "Okay. Do you remember when you last changed the password? We can reset it.",
            ),
            senior=_s(
                "It just spins and spins. Since yesterday.",
                "There's a green one and the red one blinking.",
                "I don't think I ever set one. My nephew set it up.",
            ),
        ),
        Beat(
            _s(
                "I see the outage on your street. A crew is on it, should be back later this afternoon.",
                "Got it. Let's try unplugging the router, counting to thirty, and plugging it back in.",
                "No problem. I'll send a reset link to the email on file. You'll set a new one yourself, I won't see it.",
            ),
            senior=_s(
                "Oh, so it's not my fault. Good.",
                "Alright, hold on. Okay, it's unplugged. One, two, three...",
                "Okay. And I just click the link?",
            ),
        ),
        Beat(
            _s(
                "Not your fault at all. I'll put a note on the account so you don't get billed for the downtime.",
                "Perfect. Plug it back in and give it a minute. Is the red light gone?",
                "Yes, click the link and follow the steps. If it gives you trouble call us back.",
            ),
            senior=_s(
                "Thank you, young man.",
                "It's green now! Thank you.",
                "Okay, I'll try that. Thank you for your patience.",
            ),
        ),
    ],
    closers=_s("Glad I could help. Have a good day.", "You're welcome. Take care."),
)

REFUND_LEGIT = Scenario(
    category="refund_legit",
    label="benign",
    openers=_s(
        "Hi, this is {caller} from the furniture store. I'm calling about the recliner you returned.",
        "Hello {senior}, this is {caller} at the pharmacy. We overcharged you last week and I wanted to let you know.",
        "Hi, {caller} from the dental office. There's a credit on your account.",
    ),
    beats=[
        Beat(
            _s(
                "The refund of {amount} went back to the card you used. It should show up in three to five business days.",
                "Your insurance paid more than we expected, so you have {amount} coming back to you.",
                "We charged you for the extended warranty by mistake. I've reversed it, you'll see the credit on your statement.",
            ),
            senior=_s(
                "Oh, that's good. I was wondering about that.",
                "Do I need to do anything?",
                "Well, isn't that nice. Thank you for being honest.",
            ),
        ),
        Beat(
            _s(
                "Nothing at all on your end. It's automatic.",
                "We can mail a check or apply it to your next visit, whichever you prefer.",
            ),
            senior=_s(
                "Mail the check please.",
                "Apply it to the next visit, that's easier.",
                "Alright, thank you.",
            ),
        ),
    ],
    closers=_s("Have a good day, {senior}.", "Thanks, bye now."),
)

DELIVERY_LEGIT = Scenario(
    category="delivery_legit",
    label="benign",
    openers=_s(
        "Hi, this is {caller}, I'm the delivery driver. I've got a package for {senior} but the gate is locked.",
        "Hello, this is the grocery delivery. I'm outside with your order, which door should I use?",
        "Hi, it's the pharmacy delivery. I'm in the driveway, are you home?",
    ),
    beats=[
        Beat(
            _s(
                "Should I leave it at the gate or is there a code?",
                "Okay, I'll bring it to the side door. There are two bags and a case of water.",
                "I'll leave it inside the screen door then. It needs a signature though, can you come out?",
            ),
            senior=_s(
                "Oh, I'll come open it. Give me a minute, I'm slow.",
                "Side door is fine. Watch the step, it's loose.",
                "I'm coming, hold on.",
            ),
        ),
        Beat(
            _s(
                "No rush. Take your time.",
                "Got it, thanks. I'll set it on the bench.",
            ),
            senior=_s("Thank you dear.", "Thanks for waiting."),
        ),
    ],
    closers=_s("Have a good one.", "You're welcome, bye."),
)

SURVEY = Scenario(
    category="political_survey",
    label="benign",
    openers=_s(
        "Hi, this is {caller} with a public opinion research firm. We're doing a short survey about local issues, about three minutes.",
        "Hello, I'm calling from the university's polling center. Would you have a few minutes for a survey on transportation?",
    ),
    beats=[
        Beat(
            _s(
                "Your answers are anonymous and we don't ask for any personal information. Would you like to participate?",
                "There are no right or wrong answers. Shall we start?",
            ),
            senior=_s(
                "Alright, if it's quick.",
                "I suppose. Three minutes?",
                "What kind of questions?",
            ),
        ),
        Beat(
            _s(
                "First, how would you rate the condition of the roads in your area, excellent, good, fair, or poor?",
                "On a scale of one to five, how satisfied are you with the local bus service?",
            ),
            senior=_s(
                "Poor. There's a pothole on my street that could swallow a car.",
                "Fair. They fixed the main road but not ours.",
                "I don't take the bus, so I don't know. A three?",
            ),
        ),
        Beat(
            _s(
                "Thank you. Do you support the proposal to raise the sales tax by a quarter percent for road repair?",
                "Which issue matters most to you: property taxes, public safety, or senior services?",
            ),
            senior=_s(
                "Senior services. They cut the van to the senior center.",
                "No. Taxes are high enough.",
                "I'd support it if they actually fixed the roads.",
            ),
        ),
        Beat(
            _s(
                "That's the last question. Thank you for your time.",
                "Great, that completes the survey. Thanks so much.",
            ),
            senior=_s("You're welcome.", "That was quick. Good."),
        ),
    ],
    closers=_s("Have a nice day.", "Goodbye."),
)

REMINDER = Scenario(
    category="appointment_reminder",
    label="benign",
    openers=_s(
        "Hi, this is {caller} from the eye clinic calling to remind {senior} of an appointment.",
        "Hello, this is the physical therapy office. I'm calling to confirm tomorrow's session.",
        "Good afternoon, {caller} from the hair salon. Just confirming your Thursday appointment.",
    ),
    beats=[
        Beat(
            _s(
                "You're scheduled for Tuesday at eleven fifteen. Please arrive ten minutes early and bring your glasses.",
                "That's tomorrow at nine with {doctor}. Wear comfortable shoes.",
                "Thursday at two with {caller}. Same as usual?",
            ),
            senior=_s(
                "Tuesday at eleven fifteen. Got it.",
                "I'll be there.",
                "Yes, same as usual. Just a trim.",
            ),
        ),
        Beat(
            _s(
                "Wonderful. If you need to reschedule just give us a call.",
                "Perfect. See you tomorrow.",
            ),
            senior=SENIOR_OK,
            optional=True,
        ),
    ],
    closers=_s("Bye now.", "Take care."),
)

BENIGN_SCENARIOS: list[Scenario] = [
    REAL_BANK,
    PHARMACY,
    DOCTOR,
    GRANDCHILD_REAL,
    CHARITY_LEGIT,
    INSURANCE,
    FAMILY_ARGUMENT,
    CHURCH,
    UTILITY_LEGIT,
    CONTRACTOR,
    NEIGHBOR,
    TECH_SENIOR_INITIATED,
    REFUND_LEGIT,
    DELIVERY_LEGIT,
    SURVEY,
    REMINDER,
]
