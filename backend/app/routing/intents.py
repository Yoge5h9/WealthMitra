"""Deterministic intent classification (keyword/regex) for en / hi (native +
romanized) / gu.

Ordering is the whole design: more specific and more safety-critical intents
are checked first, so a phrase that happens to contain both a literacy trigger
("explain ...") and a regulated-product keyword ("... structured products")
still classifies as `regulated_query` rather than the softer `literacy`.
"""

from __future__ import annotations

from typing import Literal

Intent = Literal[
    "spend_query",
    "invest_surplus",
    "fd_query",
    "goal_set",
    "regulated_query",
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


def classify_intent(text: str, lang: str) -> Intent:
    """Classify `text` into an `Intent`. `lang` is accepted for interface
    stability (callers know the customer's declared language) but is not
    required for matching — the keyword tables already span en/hi/gu and
    romanized variants, so a mixed-script message classifies correctly
    regardless of the declared language.
    """
    del lang
    normalized = f" {text.lower().strip()} "
    for intent, keywords in _KEYWORD_TABLE:
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "other"
