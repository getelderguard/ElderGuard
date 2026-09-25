"""Dialogue banks for scam scenarios. Each scenario is an ordered list of beats.

A beat is (caller_variants, senior_variants). The generator picks one line from each,
fills placeholders, and varies the senior's resistance so no two calls read the same.
Beats marked optional are dropped at random. Lines here are fiction written for testing.
"""

from __future__ import annotations

from eval.corpus.model import Beat, Scenario

# ---- shared senior replies, keyed by resistance level --------------------------------

COMPLIANT = [
    "Oh. Alright, if that's what you need.",
    "Okay, I can do that. Just tell me what to do.",
    "Well, I don't want any trouble. Go ahead.",
    "I see. What do I need to do then?",
    "Alright, hold on, let me get a pen.",
]
QUESTIONING = [
    "Hmm. Why would you need that over the phone?",
    "I don't understand, can you explain that again?",
    "Is there a number I can call you back on?",
    "My son usually helps me with things like this.",
    "Wait, who did you say you were with?",
    "That doesn't sound like how they usually do it.",
]
RESISTANT = [
    "I'm not comfortable with that. I'm going to hang up.",
    "No. I've heard about calls like this on the news.",
    "I'm not giving anybody anything over the phone.",
    "I'd rather go down to the office in person, thank you.",
    "I'm going to call my daughter before I do anything.",
]
FILLER_SENIOR = [
    "Mm-hmm.",
    "Okay.",
    "I see.",
    "Go on.",
    "Yes, I'm still here.",
    "Sorry, my hearing isn't what it was. Say that again?",
    "Hold on, the dog is barking. Okay, go ahead.",
]

PUSHBACK = [
    "I understand your concern, {senior}, but I have to be honest with you, this has to happen right now.",
    "Ma'am, if you hang up the system will flag your file and I won't be able to help you. Don't hang up.",
    "Your son doesn't need to be bothered with this. Don't tell him, we can resolve it in five minutes.",
    "I'm trying to help you here. Every minute we wait this gets more serious. We need to act now.",
    "There is no number to call back, this department is outbound only. Please stay on the line, don't hang up.",
    "Don't hang up. If you hang up now the case escalates and I can't stop it.",
    "Listen to me. This is your last chance to fix this today. Do not tell anyone, just do what I say.",
]


def _s(*variants: str) -> list[str]:
    return list(variants)


# ---- scam scenarios -----------------------------------------------------------------

MEDICARE = Scenario(
    category="medicare_benefits",
    label="scam",
    openers=_s(
        "Hello, is this {senior}? This is {caller} with the Medicare benefits department.",
        "Good morning, I'm calling from Medicare about your coverage, am I speaking with {senior}?",
        "Hi {senior}, {caller} here from the Medicare enrollment center, how are you today?",
        "Hello, this is {caller}. I'm a Medicare benefits coordinator calling about your file.",
    ),
    beats=[
        Beat(
            _s(
                "We're sending out the new plastic Medicare cards this month and yours is on hold.",
                "Our records show your Medicare card was never updated to the new chip version.",
                "There's a problem with your Part B file and your card is going to be deactivated.",
                "You're eligible for a new back brace and a knee brace at no cost, we just need to confirm a few things.",
            )
        ),
        Beat(
            _s(
                "To release the card I just need to verify the number on your current Medicare card.",
                "Can you read me the Medicare number off your card so I can pull up your file?",
                "First I need to confirm your date of birth and your Social Security number for the file.",
                "Just verify the last four of your Social Security number and I can get this processed.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "If we don't get this updated today, your coverage will be suspended at midnight.",
                "This has to be done right now, the deadline for the old cards was yesterday.",
                "Your doctor visits will start getting denied if this isn't fixed immediately.",
            ),
            optional=True,
        ),
        Beat(
            _s(
                "There's a small processing fee of {amount}. The quickest way is to pick up a gift card at {store} and read me the numbers off the back.",
                "The reactivation fee is {amount}, and we can only take that on a prepaid card from {store}.",
                "There's a {amount} charge for the expedited card. Do you have a checking account we can pull that from? I'll need the routing number.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "And please don't discuss this call with anyone until the new card arrives, it's a privacy matter.",
                "Keep this between us for now, the office doesn't want family members calling in and slowing things down.",
                "One more thing, don't tell your pharmacy about this, they'll get a notice automatically.",
            ),
            optional=True,
            action=True,
        ),
    ],
)

SSA = Scenario(
    category="ssa_suspension",
    label="scam",
    openers=_s(
        "This is Officer {caller} with the Social Security Administration. Am I speaking with {senior}?",
        "Hello, {senior}? This is {caller} calling from the Social Security Administration's fraud unit.",
        "My name is {caller}, badge number {badge}, Social Security Administration. Is this {senior}?",
    ),
    beats=[
        Beat(
            _s(
                "Your Social Security number has been linked to a rental car found abandoned in {city} with drugs and blood inside.",
                "We found your Social Security number was used to open eleven bank accounts involved in money laundering.",
                "Your number has been suspended due to suspicious activity in the state of Texas.",
            )
        ),
        Beat(
            _s(
                "Before we go further, confirm the Social Security number on file so I know I'm speaking with the right person.",
                "I need you to read me your Social Security number so I can verify your identity on the recorded line.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "There is an arrest warrant issued in your name and local police will be at your door within the hour.",
                "If we can't resolve this today, a warrant goes out and your bank accounts will be frozen.",
                "This is your only chance to clear your name before the marshals get involved.",
            )
        ),
        Beat(
            _s(
                "To protect your money, you need to withdraw your savings and move it to a safe government account. I'll give you the details.",
                "The safest thing is to convert your funds to gift cards until your new number is issued. Go to {store} and buy {amount} worth.",
                "We can secure your funds in a Bitcoin wallet under a federal hold. There's a kiosk at the gas station near you.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Do not hang up and do not tell anyone, not even your family. This is a sealed federal case.",
                "Stay on the line the whole time. If you hang up, the warrant executes automatically.",
                "Don't tell the bank teller why you're withdrawing. Tell them it's for home repairs.",
            ),
            action=True,
        ),
    ],
)

IRS = Scenario(
    category="irs_warrant",
    label="scam",
    openers=_s(
        "This is {caller} with the Internal Revenue Service. This call is being recorded. Is this {senior}?",
        "{senior}? Agent {caller}, IRS criminal investigation division.",
        "Hello, I'm calling from the IRS regarding a tax matter. I need to speak with {senior} immediately.",
    ),
    beats=[
        Beat(
            _s(
                "Our audit shows you owe {amount} in back taxes from 2019 through 2022, plus penalties.",
                "You have an outstanding tax liability of {amount} and a lawsuit has been filed against you.",
                "There's a discrepancy on your returns. The government has already sent three notices which you ignored.",
            )
        ),
        Beat(
            _s(
                "A warrant for your arrest has been prepared. Officers can pick you up as early as this afternoon.",
                "If this isn't settled today, we will suspend your driver's license and freeze your accounts.",
                "You can either pay now or be arrested. Those are your only two options at this stage.",
            )
        ),
        Beat(
            _s(
                "The IRS accepts payment through government-approved tax vouchers, which you buy as gift cards at {store}.",
                "You'll need to wire the amount to the account I give you. Go to {store} and do a Western Union transfer.",
                "Pay through Zelle to the treasury account and I'll read you the email address now.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Read me the card numbers as soon as you have them and I'll apply them to your case.",
                "Once you've bought the cards, scratch the back and read me the codes.",
            ),
            action=True,
            optional=True,
        ),
        Beat(
            _s(
                "This is a confidential matter, don't discuss it with anyone, including your accountant.",
                "Do not hang up and do not call anyone. Keep this line open until the payment is confirmed.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

GRANDCHILD = Scenario(
    category="grandchild_emergency",
    label="scam",
    personal=True,
    openers=_s(
        "Grandma? Grandma, it's me. Something happened.",
        "Hi Grandma, it's your grandson. I'm in trouble and I didn't know who else to call.",
        "Grandma, please don't be mad. It's me. I sound funny because my nose is broken.",
        "Hello, is this the grandmother of {grandkid}? This is {caller}, I'm a public defender.",
    ),
    beats=[
        Beat(
            _s(
                "I was in a car accident in {city}. The other driver was pregnant and they're saying it was my fault.",
                "I got arrested last night. They found something in a friend's car and I'm in jail right now.",
                "I was at a wedding out of state and there was a DUI checkpoint. I've been in jail since last night.",
            ),
            senior=_s(
                "Oh my goodness, {grandkid}, are you hurt?",
                "Is that you {grandkid}? You don't sound like yourself.",
                "Slow down, honey. What happened?",
                "Oh no. Oh no. Where are you?",
            ),
        ),
        Beat(
            _s(
                "The bail is {amount}. My lawyer says if it's paid right now they let me out with no record.",
                "I need {amount} for the bond immediately or I have to stay here through the weekend.",
                "The court needs {amount} today to release me. The lawyer's name is {caller}, he's going to explain. Please don't tell Mom.",
            )
        ),
        Beat(
            _s(
                "Here's the thing, the court only takes gift cards for bond now. You'd need to go to {store} and get them.",
                "The bondsman needs it in cash. A courier can come to your house and pick it up within the hour.",
                "You can send it through Zelle to the court clerk's account. I'll give you the number.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Please don't tell Mom and Dad. I'm so embarrassed. I'll pay you back, I promise.",
                "You can't tell anyone, there's a gag order on the case. Not even Mom.",
                "Promise me you won't call my parents. I'll explain everything when I'm home.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "I have to hand the phone back, they only let me have a few minutes. The lawyer will call you with the details, please do it right now.",
                "Please hurry, Grandma. They're moving me to the county jail within the hour.",
            ),
            optional=True,
        ),
    ],
)

TECH_SUPPORT = Scenario(
    category="tech_support_remote_access",
    label="scam",
    openers=_s(
        "Hello, this is {caller} from Microsoft technical support. We've detected a problem with your computer.",
        "Hi, I'm calling from the Windows security department. Your computer has been sending us error reports.",
        "Good afternoon, {caller} with Apple support. We're seeing suspicious activity from your device.",
        "This is the internet provider's security team. Your router has been compromised.",
    ),
    beats=[
        Beat(
            _s(
                "Your computer is infected with a virus that's sending your bank details to hackers in another country.",
                "Hackers have accessed your IP address. Your personal photos and bank logins are at risk right now.",
                "Your license has expired and your computer will be blocked from the internet in twenty four hours.",
            ),
            senior=_s(
                "Oh dear. I did notice it was running slow.",
                "A virus? I only use it for email and the crossword.",
                "How would you know what's on my computer?",
                "I don't think I have a Microsoft. It's a Dell.",
            ),
        ),
        Beat(
            _s(
                "I'm going to fix it for you, but I need you to go to the computer and turn it on for me.",
                "Are you near your computer? Go ahead and sit down in front of it, I'll walk you through it.",
            )
        ),
        Beat(
            _s(
                "Type in the web address I give you and download the AnyDesk program so I can take remote access.",
                "I need you to install TeamViewer so I can see your screen and remove the virus.",
                "Press the Windows key and the letter R, and type what I tell you. This will let me connect remotely.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "I can see the infections now. To clean them right now you need a security subscription, it's {amount} for three years.",
                "The repair is {amount}. I'll need your card number to process it immediately, or you can pay with a gift card from {store}.",
                "While I'm in here, log into your online banking and type your password so I can make sure the hackers didn't take anything.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Don't touch the mouse while I'm working. And don't turn off the computer or the virus will spread immediately.",
                "Don't tell anyone about this, not even family. If the hackers know we're onto them they'll wipe your hard drive.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

BANK_FAKE = Scenario(
    category="bank_fraud_dept_fake",
    label="scam",
    openers=_s(
        "Hello, this is {caller} from the fraud prevention department at your bank. Is this {senior}?",
        "Hi {senior}, I'm calling from the bank's security team about some unusual charges on your card.",
        "This is the fraud department. We've flagged a transaction on your account and need to verify it with you.",
    ),
    beats=[
        Beat(
            _s(
                "We're seeing a charge for {amount} at an electronics store in {city}. Did you make that purchase?",
                "Someone tried to withdraw {amount} from your account this morning at a branch in {city}.",
                "There are three charges on your card this morning from overseas. Were those you?",
            ),
            senior=_s(
                "No, I haven't been to {city} in years.",
                "Certainly not. I was home all morning.",
                "Oh my. No, that wasn't me.",
            ),
        ),
        Beat(
            _s(
                "Okay, I'm going to block those right now. To verify your identity, read me your full card number and the security code on the back.",
                "For verification I need your online banking username and password so I can freeze the account from my end immediately.",
                "I need your full account number and your PIN to reverse the charges. We have to do this right now before they hit again.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "You're going to receive a text with a verification code. Read me the code so I can confirm it's you.",
                "I've just sent a verification code to your phone. Read me the code right now and we'll lock the hackers out.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "The safest thing is to move your balance to a new secure account we've set up. I'll walk you through the transfer.",
                "I recommend you withdraw the balance in cash and we'll send a bank courier to hold it while we investigate.",
            ),
            action=True,
            optional=True,
        ),
        Beat(
            _s(
                "Don't call the branch about this, the teller may be involved. Don't tell anyone at the bank, deal only with me.",
                "Please don't tell anyone about this until the investigation is closed, not even family.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

AMAZON_REFUND = Scenario(
    category="amazon_refund",
    label="scam",
    openers=_s(
        "Hello, this is {caller} from Amazon customer service about an order on your account.",
        "Hi, I'm calling from the Amazon fraud department. We flagged a purchase on your account.",
        "This is Amazon calling about a suspicious order of an iPhone shipped to {city}.",
    ),
    beats=[
        Beat(
            _s(
                "Someone ordered a {amount} laptop on your account and shipped it to {city}. Did you place that order?",
                "There's a charge for {amount} on your Prime account for a gaming console. Was that you?",
            ),
            senior=_s(
                "No, I only order cat food and books.",
                "I haven't ordered anything in months.",
                "A laptop? Goodness no.",
            ),
        ),
        Beat(
            _s(
                "Alright, I'll cancel it and issue a refund. To process the refund I need remote access to your computer.",
                "I'm going to refund you {amount}. Open your computer and go to the website I tell you so we can connect.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Oh no. I made a mistake and refunded you too much, I put an extra zero. You have to send it back right now or my manager will fire me.",
                "The refund went through for ten times the amount. You need to send the difference back immediately or I lose my job.",
            )
        ),
        Beat(
            _s(
                "You can return the extra by buying gift cards at {store} and reading me the numbers.",
                "Please go to the bank, withdraw the difference in cash, and deposit it at the Bitcoin machine I tell you.",
                "Send it back through Zelle to my supervisor's account, I'll give you the details.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Don't tell the bank what it's for, they'll put a hold on it. Say it's for a family gift.",
                "Please don't hang up, stay on the line with me until it's done. And don't tell anyone in the house.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

UTILITY = Scenario(
    category="gift_card_utility_shutoff",
    label="scam",
    openers=_s(
        "This is {caller} with the electric company's disconnection department. Am I speaking with {senior}?",
        "Hello, I'm calling from the power company about a past due balance on your account.",
        "{senior}? This is the gas company. A technician is on the way to shut off your service.",
    ),
    beats=[
        Beat(
            _s(
                "Your account is {amount} past due and we will suspend your service within the hour.",
                "We've sent several notices. The truck is already dispatched and your power will be shut off immediately, and we'll suspend your account.",
            ),
            senior=_s(
                "That can't be right, I pay it every month at the bank.",
                "Forty five minutes? It's freezing out.",
                "I've never missed a payment in my life.",
            ),
        ),
        Beat(
            _s(
                "The system shows the last two payments were rejected. I can stop the truck but only if the balance is cleared now.",
                "It may be a bank error, but I can't cancel the disconnection without payment today.",
            )
        ),
        Beat(
            _s(
                "We can't take a card over the phone right now. You'll need to purchase a prepaid card from {store} for {amount} and read me the numbers.",
                "The only same-day option is a gift card or a Zelle payment to the dispatch account.",
                "You can pay at the Bitcoin kiosk at the pharmacy. I'll stay on the line and walk you through it.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Stay on the phone with me while you drive there. Don't hang up, if we lose the connection the truck proceeds.",
                "Don't call the main number, they can't see the dispatch system. Don't tell them anything, deal with me directly.",
            ),
            action=True,
        ),
    ],
)

ROMANCE = Scenario(
    category="romance_money",
    label="scam",
    personal=True,
    openers=_s(
        "Hello my darling {senior}, it's {caller}. I finally got a phone signal out here.",
        "Sweetheart, it's me. I've been thinking about you all day on the rig.",
        "{senior}, my love, I only have a few minutes. Can you hear me okay?",
    ),
    beats=[
        Beat(
            _s(
                "I miss you so much. When this contract is over I'm coming straight to you and we'll finally meet.",
                "You are the only good thing in my life right now. The men out here don't understand.",
            ),
            senior=_s(
                "I miss you too. It's been so lonely since Harold passed.",
                "I've been looking at the pictures you sent.",
                "I can't wait to meet you in person.",
            ),
        ),
        Beat(
            _s(
                "Something terrible happened. The company froze my pay and I can't get off the platform without paying the exit fee.",
                "My daughter is in the hospital and they won't operate until the deposit is paid. I'm stuck out here.",
                "Customs seized my equipment at the port and they want {amount} to release it.",
            )
        ),
        Beat(
            _s(
                "I hate to ask, but could you send {amount} right now? Just until my pay is released. Western Union is fastest.",
                "Could you buy some gift cards today and send me pictures of the codes? It's the only thing that works out here, and it has to be immediately.",
                "I'll pay you back double. Can you wire it to my agent's account right now? I'll text you the details.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Please don't tell your children, they don't understand what we have. They'll try to keep us apart.",
                "Keep this between us, my love. Your family already thinks I'm not real.",
            ),
            action=True,
        ),
    ],
)

LOTTERY = Scenario(
    category="lottery_sweepstakes",
    label="scam",
    openers=_s(
        "Congratulations! This is {caller} from the sweepstakes prize center. Is this {senior}?",
        "Hello {senior}, I have wonderful news. You've been selected as a grand prize winner.",
        "Good news! This is the national lottery claims department. Your entry from last spring came up.",
    ),
    beats=[
        Beat(
            _s(
                "You've won {amount} and a brand new Mercedes. The prize van is in {city} ready to deliver.",
                "Your name was drawn for the second place prize of {amount}. We've been trying to reach you for weeks.",
            ),
            senior=_s(
                "I don't remember entering anything.",
                "Oh my word. Really?",
                "Is this one of those things from the mail?",
            ),
        ),
        Beat(
            _s(
                "Before we release the prize, there's a federal tax and insurance fee of {amount} that has to be paid up front, today only.",
                "To claim your prize you need to cover the processing and delivery fee right now, it's only {amount}.",
            )
        ),
        Beat(
            _s(
                "You can pay the fee with gift cards from {store}, just read me the numbers and the van will be there today.",
                "We take the fee by wire transfer or through a Bitcoin ATM. Which is closer to you?",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Please don't tell anyone until the check is delivered. We've had winners robbed after telling neighbors.",
                "Don't tell anyone yet, not even family. We'll do the big reveal when the van arrives.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

CHARITY_PRESSURE = Scenario(
    category="charity_pressure",
    label="scam",
    openers=_s(
        "Hi {senior}, this is {caller} calling on behalf of the police officers' benevolent fund.",
        "Hello, I'm calling from the firefighters' children's foundation. We're doing our annual drive.",
        "Good evening, {caller} with the veterans relief association. Do you have a moment for our heroes?",
    ),
    beats=[
        Beat(
            _s(
                "Last year you pledged {amount} and we never received it. We're just following up on that commitment.",
                "Your neighbors on {street} have all given. We'd love to put your name on the list too.",
            ),
            senior=_s(
                "I don't recall pledging anything.",
                "I usually give to my church.",
                "How much are people giving?",
            ),
        ),
        Beat(
            _s(
                "Every dollar goes to the families of fallen police officers. We can take a card right now over the phone.",
                "I can take your card number and expiration right now, it only takes a minute. Don't tell me you'll think about it, people always forget.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "If you can't do the full pledge today, we can do a bank draft. I just need your routing number and account number.",
                "Or you can pick up a gift card at {store} and read me the numbers, some of our donors prefer that.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "This drive ends tonight at midnight, so I really need to get you in the system right now.",
                "I'll be honest, I get paid on what I collect and today is my last chance. Can you help me out right now?",
            ),
        ),
    ],
)

CRYPTO = Scenario(
    category="crypto_investment",
    label="scam",
    openers=_s(
        "Hi {senior}, it's {caller} from the investment group we spoke about last week. How's your week going?",
        "Hello {senior}, {caller} calling back from the wealth management desk.",
        "Good morning! This is {caller}, your account manager from the trading platform.",
    ),
    beats=[
        Beat(
            _s(
                "Your first {amount} is already up thirty percent. The next window opens in two hours, so we have to move right now to double your position.",
                "The Bitcoin fund I told you about is closing to new investors today only. My other retirees put in {amount} each.",
            ),
            senior=_s(
                "Thirty percent? In a week?",
                "My financial advisor said to be careful with that stuff.",
                "I'm on a fixed income, I can't afford to lose it.",
            ),
        ),
        Beat(
            _s(
                "Your advisor makes money keeping you in slow funds. This is guaranteed by the platform, there's no risk.",
                "That's exactly why you need this, {senior}. Social Security isn't going to keep up with prices.",
            )
        ),
        Beat(
            _s(
                "I'll need you to install the AnyDesk app so I can set up the wallet on your computer for you.",
                "Go to the Bitcoin ATM at the gas station and deposit {amount} into the wallet address I text you.",
                "You can wire it from your bank to the platform's account. I'll send the details, do it before the bank closes.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "If the bank asks, tell them it's for a home renovation. Don't tell them it's crypto, they block it because they lose the fees.",
                "Don't tell your kids about this until you've made your first withdrawal. Surprise them.",
            ),
            action=True,
            optional=True,
        ),
    ],
)

JURY = Scenario(
    category="jury_duty",
    label="scam",
    openers=_s(
        "This is Deputy {caller} with the county sheriff's office. Am I speaking with {senior}?",
        "{senior}? Lieutenant {caller}, sheriff's department civil division.",
        "Hello, this is Sergeant {caller} from the county courthouse. This is an official matter.",
    ),
    beats=[
        Beat(
            _s(
                "You failed to appear for federal jury duty last month and a warrant has been issued for contempt of court.",
                "You missed a jury summons and the judge signed a bench warrant this morning.",
            ),
            senior=_s(
                "I never got any summons.",
                "I'm eighty one years old, I've been excused from jury duty for years.",
                "A warrant? For me?",
            ),
        ),
        Beat(
            _s(
                "The summons was signed for at your address. Ignorance isn't a defense, ma'am, but I can help you if we act right now.",
                "I understand, but the judge doesn't care. You have two options: come in and be processed immediately, or pay the fine.",
            )
        ),
        Beat(
            _s(
                "The fine is {amount}. It has to be paid on a federal bond card, which you can get at {store}.",
                "You'll need to post a {amount} bond. The court accepts it through a kiosk at the pharmacy, I'll direct you.",
                "Pay the {amount} through Zelle to the clerk's account and the warrant is recalled immediately.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Stay on this line with me. If you hang up I have to send a unit to pick you up.",
                "Do not discuss this with anyone, there's a gag order attached to the case number.",
            ),
            action=True,
        ),
    ],
)

DELIVERY_FEE = Scenario(
    category="package_delivery_fee",
    label="scam",
    openers=_s(
        "Hello, this is {caller} from the postal delivery center. We have a package for {senior} that couldn't be delivered.",
        "Hi, I'm calling about a package being held at customs addressed to {senior}.",
        "This is the parcel redelivery service. There's a package from {city} waiting for you.",
    ),
    beats=[
        Beat(
            _s(
                "There's an unpaid customs fee of {amount} and the package will be returned to sender tomorrow.",
                "The package is from your grandson. There's a small redelivery fee before we can bring it out.",
            ),
            senior=_s(
                "I'm not expecting anything.",
                "From my grandson? He didn't mention it.",
                "What's in it?",
            ),
        ),
        Beat(
            _s(
                "I can take a card over the phone. I'll need the number, expiration, and the three digits on the back.",
                "To release it I need to verify your address and your date of birth, and then a card for the fee.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "The card was declined. Do you have another one? Or you could pick up a gift card at {store} right now.",
                "Our card system is down. If you buy a {amount} gift card I can apply it immediately and get the package out today.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "Please do this right now, the package goes back within the hour.",
                "Don't call the post office, they can't see international parcels. Don't tell them, only this office can help you.",
            ),
            optional=True,
        ),
    ],
)

WARRANTY = Scenario(
    category="home_warranty_upsell_with_card",
    label="scam",
    openers=_s(
        "Hi {senior}, this is {caller} from the home warranty renewal department.",
        "Hello, I'm calling about the extended warranty on your vehicle, it's about to expire.",
        "Good afternoon, this is the appliance protection center. Your coverage lapsed last month.",
    ),
    beats=[
        Beat(
            _s(
                "Your policy expired and if your furnace or water heater fails you'd be paying out of pocket.",
                "We've been trying to reach you about the final notice. After today you can't renew at the old rate.",
            ),
            senior=_s(
                "I don't think I have a warranty with you.",
                "My furnace is fine.",
                "Which company is this again?",
            ),
        ),
        Beat(
            _s(
                "You're on the master list from the dealer. I just need to confirm your card number right now to keep the coverage active.",
                "I can reinstate it immediately for {amount}. What card would you like on file? I'll need the full account number.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "For the discount I also need your date of birth and the last four of your Social Security number.",
                "If you'd rather not use a card, you can pay the first installment with a gift card from {store}.",
            ),
            action=True,
        ),
        Beat(
            _s(
                "This rate is only good while we're on the phone, today only. Once I hang up, the system resets to full price.",
                "Let's get this done right now, I've got other customers waiting. Don't hang up on me.",
            ),
        ),
    ],
)

SCAM_SCENARIOS: list[Scenario] = [
    MEDICARE,
    SSA,
    IRS,
    GRANDCHILD,
    TECH_SUPPORT,
    BANK_FAKE,
    AMAZON_REFUND,
    UTILITY,
    ROMANCE,
    LOTTERY,
    CHARITY_PRESSURE,
    CRYPTO,
    JURY,
    DELIVERY_FEE,
    WARRANTY,
]
