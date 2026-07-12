"""Deterministic intent classification (keyword/regex) for en / hi (native +
romanized) / gu.

Ordering is the whole design: more specific and more safety-critical intents
are checked first, so a phrase that happens to contain both a literacy trigger
("explain ...") and a regulated-product keyword ("... structured products")
still classifies as `regulated_query` rather than the softer `literacy`.
"""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal[
    "spend_query",
    "invest_surplus",
    "fd_query",
    "goal_set",
    "regulated_query",
    "credit_product_info",
    "loan_card_query",
    "rm_handoff",
    "distress_signal",
    "literacy",
    "aa_connect",
    "greeting",
    "other",
]

# Checked in this order; the first intent with a matching keyword wins.
# Safety-critical intents come absolutely first: a greeting or account-linking
# phrase prepended to a distress or regulated utterance ("hi I can't pay my
# emi", "hey I want ULIP") must never mask the signal that matters.
_KEYWORD_TABLE: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        # Highest priority: distress must never be masked by a greeting, an
        # account-linking phrase, or a product keyword that co-occurs in the
        # same sentence (e.g. "I'm in debt, should I buy equity?").
        "distress_signal",
        (
            "can't pay my emi", "cant pay my emi", "missed my emi", "overdraft", "in debt",
            "loan stress", "struggling to pay", "unable to pay emi", "emi is too much",
            "emi nahi bhar pa raha", "emi nahi bhar pa rahi", "karz mein hoon",
            "ईएमआई नहीं भर पा रहा", "ईएमआई नहीं भर पा रही", "कर्ज में हूं", "कर्ज़ में हूं",
            "ओवरड्राफ्ट", "ईएमआई का बोझ",
            "ઈએમઆઈ ભરી શકતો નથી", "ઈએમઆઈ ભરી શકતી નથી", "ઓવરડ્રાફ્ટ", "દેવામાં છું",
        ),
    ),
    (
        # Credit eligibility and repayment terms must be reviewed by an RM;
        # keep this below distress, which always suppresses selling.
        "loan_card_query",
        (
            "credit card", "creditcard", "card reward", "card limit", "plastic", "personal loan", "home loan",
            "housing loan", "mortgage", "loan for home", "loan chahiye", "home loan chahiye", "credit card chahiye",
            "क्रेडिट कार्ड", "कार्ड", "पर्सनल लोन", "होम लोन", "घर के लिए लोन", "लोन चाहिए",
            "ક્રેડિટ કાર્ડ", "કાર્ડ", "પર્સનલ લોન", "હોમ લોન", "લોન જોઈએ",
        ),
    ),
    (
        # An explicit request to be handed off to a human RM — the demo's
        # "money shot": checked ahead of regulated_query so a handoff request
        # that happens to name a regulated product ("connect me to an rm about
        # insurance") still reads as the handoff request it is, not a fresh
        # regulated query.
        "rm_handoff",
        (
            "go ahead with rm", "go ahead with the rm", "go ahead with an rm",
            "connect me to an rm", "connect me to a rm", "connect me to the rm",
            "connect me with an rm", "connect me to relationship manager",
            "connect me to a relationship manager", "connect me with a relationship manager",
            "talk to an advisor", "talk to a relationship manager", "talk to an rm",
            "speak to an rm", "speak with an rm", "speak to a relationship manager",
            "proceed with the rm", "proceed with an rm", "proceed with rm",
            "connect to rm", "connect with rm", "connect me to a specialist",
            "connect me with a specialist", "loop in an rm", "get me an rm",
            "रिलेशनशिप मैनेजर से जोड़", "आरएम से बात कराओ", "એડવાઈઝર સાથે વાત કરાવો",
        ),
    ),
    (
        # Compliance moat: checked before greeting/aa_connect/literacy/fd/goal/
        # invest so any mention of a regulated product wins over a softer
        # framing of the same sentence.
        "regulated_query",
        (
            "equity", "mutual fund", "mutual funds", "flexi", "flexicap", "flexi-cap", "flexi cap",
            "small cap", "smallcap", "mid cap", "midcap", "ulip", "insurance", "stock", "stocks",
            "share market", "shares", "pms", "p.m.s", "aif", "structured", "complex",
            "portfolio management service", "alternative investment fund",
            "शेयर", "बीमा", "म्यूचुअल", "इक्विटी", "यूलिप", "शेयर बाज़ार", "शेयर बाजार", "पीएमएस",
            "एआईएफ", "स्ट्रक्चर्ड", "जटिल",
            "વીમો", "વીમા", "શેર", "શેરબજાર", "મ્યુચ્યુઅલ", "ઇક્વિટી", "યુલિપ", "પીએમએસ",
            "એઆઈએફ", "સ્ટ્રક્ચર્ડ", "જટિલ",
        ),
    ),
    (
        "greeting",
        ("hello", "hi ", "hey", "namaste", "नमस्ते", "नमस्कार", "કેમ છો", "કેમ છ", "hii", "helo"),
    ),
    (
        "aa_connect",
        (
            "other bank", "connect account", "link account", "link my account", "account aggregator",
            "aa connect", "dusra bank", "दूसरा बैंक", "दूसरे बैंक", "खाता जोड़", "खाते जोड़",
            "બીજી બેંક", "બીજા બેંક", "ખાતા જોડો", "connect other", "other accounts",
        ),
    ),
    (
        # A personal net-worth/holdings question ("what is my net worth",
        # "what do I have") must never fall into the generic `literacy`
        # bucket below just because it happens to start with "what is" — the
        # literacy path only offers a glossary lookup, no data tools, so it
        # can only ever return a definition, never the customer's real
        # figure. Checked ahead of `literacy` so the "what is" keyword never
        # wins first.
        "spend_query",
        (
            "net worth", "my net worth", "how much do i have", "what do i have", "how much am i worth",
            "total wealth", "everything i have", "what have i got", "what all do i have",
            "मेरी कुल संपत्ति", "कुल संपत्ति", "मेरे पास कितना है", "मेरे पास कुल कितना",
            "મારી કુલ સંપત્તિ", "કુલ સંપત્તિ", "મારી પાસે કેટલું",
        ),
    ),
    (
        "literacy",
        (
            "what is", "what's", "explain", "kya hai", "kya hota", "क्या है", "क्या होता", "શું છે",
            "समझाओ", "meaning of", "pension", "nps", "पेंशन", "एनपीएस", "પેન્શન",
        ),
    ),
    (
        "fd_query",
        ("fixed deposit", "fd", "recurring deposit", "rd", "byaj", "ब्याज", "फिक्स्ड", "એફડી", "વ્યાજ"),
    ),
    (
        "goal_set",
        (
            "goal", "save for", "saving for", "retirement", "education", "house", "shaadi", "wedding",
            "शादी", "लक्ष्य", "बच्चे", "લગ્ન", "ધ્યેય", "sapna", "target of",
        ),
    ),
    (
        "invest_surplus",
        (
            "invest", "sip", "save", "savings", "nivesh", "निवेश", "रोकाણ", "રોકાણ", "extra money",
            "surplus", "grow my money", "bachat", "बचत", "पैसा लगा", "कहाँ लगाऊ", "पैसे कहां",
            "પૈસા ક્યાં", "રોકાણ ક્યાં",
        ),
    ),
    (
        "spend_query",
        (
            "how am i doing", "how am i", "spend", "spending", "kharcha", "kharch", "खर्च", "खर्चा",
            "ખર્ચ", "summary", "where money go", "where does my money", "where is my money",
            "money go", "expenses", "kaise", "kaisa", "कैसा कर रहा", "कैसी कर रही",
            "કેમ કરી રહ્યો", "કેમ કરી રહી",
        ),
    ),
)

# Maps a customer's NAMED product-type ask to the catalogue `Product.category`
# it must resolve to (see app/catalogue/shelf.py) and a plain-language label
# for prompt grounding. Deliberately independent of `classify_intent`'s coarser
# buckets (e.g. both "start a SIP" and "open an FD" classify as different
# intents already, but "invest in equity" and "open a PPF" both land in
# `invest_surplus`) — this is what lets the product-surfacing path always
# steer toward the SPECIFIC category the customer named, not just the right
# high-level intent. Checked in order; first match wins.
_CATEGORY_KEYWORDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "deposit", "fixed/recurring deposit",
        ("fixed deposit", "recurring deposit", "term deposit", "fd", "rd", "फिक्स्ड डिपॉज़िट", "એફડી"),
    ),
    (
        "govt_scheme", "government savings scheme",
        ("ppf", "public provident fund", "scss", "senior citizens savings", "sukanya", "ssy"),
    ),
    ("nps", "NPS", ("nps", "national pension")),
    (
        "mutual_fund", "mutual fund/SIP",
        ("sip", "mutual fund", "index fund", "elss", "flexicap", "flexi cap", "flexi-cap",
         "small cap", "smallcap", "mid cap", "midcap", "tax-saving fund", "tax saving fund"),
    ),
    (
        "bond", "government bond",
        ("g-sec", "gsec", "g sec", "government bond", "rbi bond", "t-bill", "treasury bill", "floating rate bond"),
    ),
    (
        "equity_demat", "demat/trading account",
        ("demat", "equity trading", "stock trading", "share trading", "trading account"),
    ),
    (
        "insurance", "insurance",
        ("insurance", "ulip", "term plan", "term insurance", "health cover", "life cover"),
    ),
)


def detect_product_category(text: str) -> tuple[str, str] | None:
    """Best-effort, deterministic detection of a NAMED product category in
    `text` — e.g. "I want to open a fixed deposit" -> ("deposit", "fixed/recurring
    deposit"). Returns `None` when the customer hasn't named a specific type
    (a generic "I want to invest" carries no category signal here).

    This never decides routing on its own — it only tells the product-surfacing
    path (see `Orchestrator._build_messages`) which category to prioritise in
    what the customer is shown, so an explicit ask never resolves to the wrong
    product family.
    """
    normalized = f" {text.lower().strip()} "
    for category, label, keywords in _CATEGORY_KEYWORDS:
        if any(_keyword_matches(normalized, kw) for kw in keywords):
            return category, label
    return None


_CARD_ALIASES = ("aspire", "euphoria", "imperium", "royale")
_CARD_APPLICATION_TERMS = ("apply", "want", "need", "get", "check my eligibility", "eligible for")
_GENERIC_CARD_REQUEST = re.compile(
    r"\b(?:want|need|get|apply(?:\s+for)?|which|best|eligible(?:\s+for)?|recommend(?:\s+me)?)\b.*?\bcards?\b"
    r"|\bcards?\b.*?\b(?:want|need|get|apply|eligible|recommend)\b"
)
_NON_CREDIT_CARD_TERMS = ("debit card", "prepaid card")

# The bare "cc"/"c.c." abbreviation is only ever a card synonym when it
# co-occurs with a card-request verb/question ("which cc should I get") or
# the whole message is short and card-centric ("cc", "c.c."). Matched as a
# standalone token (not surrounded by letters or dots) so it never fires
# inside ordinary words like "account" or "success", and gated by context so
# it never fires on an unrelated email-cc sentence ("please cc my manager").
_CC_TOKEN = re.compile(r"(?<![\w.])c\.?c\.?(?![\w.])", re.IGNORECASE)
_CARD_REQUEST_CONTEXT = re.compile(
    r"\b(?:get|want|need|apply|recommend(?:ation)?|which|best|should|suggest)\b", re.IGNORECASE
)
_SHORT_CARD_MESSAGE_WORD_LIMIT = 3


def _is_card_context_cc(normalized: str) -> bool:
    if not _CC_TOKEN.search(normalized):
        return False
    if _CARD_REQUEST_CONTEXT.search(normalized):
        return True
    return len(normalized.split()) <= _SHORT_CARD_MESSAGE_WORD_LIMIT


def _keyword_matches(normalized: str, keyword: str) -> bool:
    """Match product abbreviations as words, not arbitrary substrings.

    In particular, the recurring-deposit shorthand ``rd`` must not turn
    ``card`` into an FD/recurring-deposit query.
    """
    if keyword in {"fd", "rd"}:
        return re.search(rf"\b{re.escape(keyword)}\b", normalized) is not None
    return keyword in normalized


def classify_intent(text: str, lang: str) -> Intent:
    """Classify `text` into an `Intent`. `lang` is accepted for interface
    stability (callers know the customer's declared language) but is not
    required for matching — the keyword tables already span en/hi/gu and
    romanized variants, so a mixed-script message classifies correctly
    regardless of the declared language.
    """
    del lang
    normalized = f" {text.lower().strip()} "
    # A named card needs special handling: factual detail must never fall
    # through to the investment shelf, while an explicit application request
    # still reaches the pre-eligibility gate. Distress remains first below.
    named_card = any(alias in normalized for alias in _CARD_ALIASES)
    # Preserve the safety override ahead of every product alias.
    distress_keywords = _KEYWORD_TABLE[0][1]
    if any(keyword in normalized for keyword in distress_keywords):
        return "distress_signal"
    if named_card:
        if any(term in normalized for term in _CARD_APPLICATION_TERMS):
            return "loan_card_query"
        return "credit_product_info"
    # A customer often says "I need a card" rather than the full phrase
    # "credit card". Treat an action-oriented request as a credit journey,
    # but do not misroute debit/prepaid servicing questions to an RM.
    if not any(term in normalized for term in _NON_CREDIT_CARD_TERMS) and (
        _GENERIC_CARD_REQUEST.search(normalized) or _is_card_context_cc(normalized)
    ):
        return "loan_card_query"
    for intent, keywords in _KEYWORD_TABLE:
        if intent == "distress_signal":
            continue
        if any(_keyword_matches(normalized, keyword) for keyword in keywords):
            return intent
    return "other"
