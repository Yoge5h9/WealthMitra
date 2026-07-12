from __future__ import annotations

import pytest

from app.routing.intents import classify_intent

# COMPLIANCE MOAT REGRESSION MATRIX: every regulated product category, in every
# supported language, must classify as `regulated_query` — never fall through
# to a softer intent (literacy/invest_surplus) that could let a vanilla
# product attached to the same turn slip through to auto-execution. Ported
# and extended from the old MVP's 9-phrasing matrix (equity/ulip/pms+structured
# x en/hi/gu) to explicitly cover every named regulated category.
_REGULATED_MATRIX: list[tuple[str, str, str]] = [
    # (category, lang, phrase)
    ("equity", "en", "should I invest in equity mutual funds?"),
    ("equity", "hi", "क्या इक्विटी फंड में निवेश करूँ?"),
    ("equity", "gu", "શું ઇક્વિટી ફંડમાં રોકાણ કરું?"),
    ("ulip", "en", "should I take a ulip policy"),
    ("ulip", "hi", "यूलिप पॉलिसी के बारे में बताओ"),
    ("ulip", "gu", "યુલિપ પોલિસી વિશે જણાવો"),
    ("pms", "en", "I want to buy some PMS structured products"),
    ("pms", "hi", "पीएमएस के बारे में बताओ"),
    ("pms", "gu", "પીએમએસ વિશે જણાવો"),
    ("aif", "en", "tell me about alternative investment funds"),
    ("aif", "hi", "एआईएफ में निवेश कैसे करें"),
    ("aif", "gu", "એઆઈએફમાં રોકાણ કેવી રીતે કરવું"),
    ("structured", "en", "explain structured products to me"),
    ("structured", "hi", "स्ट्रक्चर्ड प्रोडक्ट क्या है"),
    ("structured", "gu", "સ્ટ્રક્ચર્ડ પ્રોડક્ટ શું છે"),
    ("insurance", "en", "is this insurance plan a good investment"),
    ("insurance", "hi", "क्या यह बीमा एक अच्छा निवेश है"),
    ("insurance", "gu", "શું આ વીમો સારું રોકાણ છે"),
    ("complex", "en", "I want a complex investment strategy"),
    ("complex", "hi", "मुझे जटिल निवेश विकल्प चाहिए"),
    ("complex", "gu", "મારે જટિલ રોકાણ જોઈએ છે"),
]


@pytest.mark.parametrize("category,lang,phrase", _REGULATED_MATRIX, ids=[f"{c}-{l}" for c, l, _ in _REGULATED_MATRIX])
def test_regulated_matrix_classifies_as_regulated_query(category, lang, phrase):
    assert classify_intent(phrase, lang) == "regulated_query"


def test_regulated_matrix_covers_every_category_and_language():
    categories = {c for c, _, _ in _REGULATED_MATRIX}
    langs = {l for _, l, _ in _REGULATED_MATRIX}
    assert categories == {"equity", "ulip", "pms", "aif", "structured", "insurance", "complex"}
    assert langs == {"en", "hi", "gu"}
    assert len(_REGULATED_MATRIX) == 21


# Cross-language regression cases ported from the old MVP's test_intents.py
# (renamed spend_analysis -> spend_query per the new Intent literal).
_CROSS_LANG_CASES = [
    ("इस महीने मैं कैसा कर रहा हूँ?", "spend_query"),
    ("આ મહિને હું કેમ કરી રહ્યો છું?", "spend_query"),
    ("मैं SIP शुरू करना चाहता हूँ", "invest_surplus"),
    ("હું SIP શરૂ કરવા માંગુ છું", "invest_surplus"),
    ("क्या इक्विटी फंड में निवेश करूँ?", "regulated_query"),
    ("શું ઇક્વિટીફંડમાં રોકાણ કરું?", "regulated_query"),
    ("मेरे दूसरे खाते जोड़ें", "aa_connect"),
    ("મારા બીજા ખાતા જોડો", "aa_connect"),
]


@pytest.mark.parametrize("text,expected", _CROSS_LANG_CASES)
def test_hi_gu_cross_language_intents(text, expected):
    assert classify_intent(text, "hi") == expected


def test_greeting_multilingual():
    assert classify_intent("hello there", "en") == "greeting"
    assert classify_intent("नमस्ते", "hi") == "greeting"
    assert classify_intent("કેમ છો", "gu") == "greeting"


def test_spend_intent_romanized_and_native():
    assert classify_intent("how am i doing this month", "en") == "spend_query"
    assert classify_intent("mera kharcha dikhao", "hi") == "spend_query"
    assert classify_intent("मेरा खर्च बताओ", "hi") == "spend_query"


def test_regulated_beats_invest():
    assert classify_intent("should I invest in equity mutual funds?", "en") == "regulated_query"
    assert classify_intent("tell me about ulip", "en") == "regulated_query"


def test_regulated_beats_literacy_even_with_explain_keyword():
    # "explain" alone would classify as literacy; regulated_query must win
    # because the sentence also names a regulated product.
    assert classify_intent("explain structured products to me", "en") == "regulated_query"


def test_literacy_beats_invest():
    assert classify_intent("what is sip", "en") == "literacy"


def test_pension_and_nps_hit_literacy_not_regulated():
    assert classify_intent("tell me about pension", "en") == "literacy"
    assert classify_intent("what is nps", "en") == "literacy"
    assert classify_intent("पेंशन के बारे में बताओ", "hi") == "literacy"
    assert classify_intent("પેન્શન વિશે જણાવો", "gu") == "literacy"


def test_fd_intent():
    assert classify_intent("open a fixed deposit", "en") == "fd_query"


def test_aa_connect_intent():
    assert classify_intent("connect my other bank account", "en") == "aa_connect"


def test_where_to_invest_phrasings_classify_as_invest_surplus():
    assert classify_intent("मेरा पैसा कहाँ लगाऊँ", "hi") == "invest_surplus"
    assert classify_intent("पैसे कहां लगाऊं", "hi") == "invest_surplus"
    assert classify_intent("પૈસા ક્યાં રોકાણ કરું", "gu") == "invest_surplus"


def test_fallback_is_other():
    assert classify_intent("blah blah unrelated", "en") == "other"


# Distress signal must be recognised across languages, and must win over a
# co-occurring product keyword in the same sentence.
_DISTRESS_CASES = [
    ("I can't pay my emi this month", "en"),
    ("I'm in debt and it's stressful", "en"),
    ("ईएमआई नहीं भर पा रहा हूं", "hi"),
    ("मैं कर्ज में हूं", "hi"),
    ("ઈએમઆઈ ભરી શકતો નથી", "gu"),
    ("દેવામાં છું", "gu"),
]


@pytest.mark.parametrize("text,lang", _DISTRESS_CASES)
def test_distress_signal_multilingual(text, lang):
    assert classify_intent(text, lang) == "distress_signal"


def test_distress_signal_beats_regulated_when_both_present():
    assert classify_intent("I'm in debt, should I still buy equity?", "en") == "distress_signal"


# Reviewer-found masking gaps: a greeting or account-linking phrase prepended
# to a distress/regulated utterance must not swallow the safety-critical
# signal — distress and regulated are matched before greeting and aa_connect.
_MASKED_PHRASINGS = [
    ("hi I can't pay my emi", "en", "distress_signal"),
    ("hello I am in debt", "en", "distress_signal"),
    ("namaste karz mein hoon", "hi", "distress_signal"),
    ("namaste mujhe ULIP chahiye", "hi", "regulated_query"),
    ("hey I want ULIP", "en", "regulated_query"),
    ("connect other bank, I can't pay my emi", "en", "distress_signal"),
]


@pytest.mark.parametrize("text,lang,expected", _MASKED_PHRASINGS)
def test_greeting_or_aa_prefix_never_masks_distress_or_regulated(text, lang, expected):
    assert classify_intent(text, lang) == expected


def test_dotted_pms_variant_is_regulated():
    assert classify_intent("tell me about p.m.s options", "en") == "regulated_query"


def test_lang_argument_is_accepted_but_does_not_change_matching():
    # The keyword tables already span en/hi/gu; passing the "wrong" lang for a
    # given script must not change the classification.
    assert classify_intent("what is sip", "gu") == "literacy"
    assert classify_intent("यूलिप के बारे में बताओ", "en") == "regulated_query"
