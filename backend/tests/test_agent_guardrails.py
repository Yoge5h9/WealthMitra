"""Number-audit guardrail tests — extraction across Indian formats and the
membership check against tool-sourced figures.
"""

import pytest

from app.agent import guardrails as g

# --- extraction table -------------------------------------------------------
# (text, expected list of (value, kind)) — kinds: currency | pct | plain.

EXTRACTION_TABLE = [
    ("₹1,23,456 is idle", [(123456.0, "currency")]),
    ("Rs. 5,000 monthly", [(5000.0, "currency")]),
    ("INR 85000 credited", [(85000.0, "currency")]),
    ("about 1.2 lakh sitting idle", [(120000.0, "currency")]),
    ("save 2 lakhs a year", [(200000.0, "currency")]),
    ("₹1.5 crore portfolio", [(15000000.0, "currency")]),
    ("earns 12% returns", [(12.0, "pct")]),
    ("rate of 7.4% p.a.", [(7.4, "pct")]),
    ("about 25 percent", [(25.0, "pct")]),
    ("आपके पास १,२३,४५६ रुपये हैं", [(123456.0, "plain")]),  # Devanagari digits
    ("₹१.२ लाख बचत", [(120000.0, "currency")]),  # Devanagari + लाख scale
    ("તમારી પાસે ૫૦,૦૦૦ છે", [(50000.0, "plain")]),  # Gujarati digits
    ("₹૨ કરોડનું પોર્ટફોલિયો", [(20000000.0, "currency")]),  # Gujarati crore
    ("mixed: ₹85,000 salary, 1.2 lakh idle and 7.4% return",
     [(85000.0, "currency"), (120000.0, "currency"), (7.4, "pct")]),
    ("save 15 हज़ार every month", [(15000.0, "currency")]),  # digits + hi thousand
    ("put aside 15k monthly", [(15000.0, "currency")]),  # "k" thousand shorthand
    ("ninety thousand rupees idle", [(90000.0, "currency")]),  # spelled + en scale
    ("invest two crore in assets", [(20000000.0, "currency")]),  # spelled + crore
    ("पाँच लाख का निवेश करें", [(500000.0, "currency")]),  # spelled hi + लाख
    ("અઢી લાખ બચત છે", [(250000.0, "currency")]),  # gu 2.5 + લાખ
    ("no numbers here", []),
    ("support is available 24x7", []),  # formatting token, not a claim
    ("open 24/7 every day", []),
    ("give me fifty of those", []),  # word-number WITHOUT a scale: out of scope
]


@pytest.mark.parametrize("text,expected", EXTRACTION_TABLE)
def test_extraction_table(text, expected):
    claims = [(c.value, c.kind) for c in g.extract_numbers(text)]
    assert claims == expected


def test_extraction_plain_int():
    claims = g.extract_numbers("you spent 123456 on rent")
    assert [(c.value, c.kind) for c in claims] == [(123456.0, "plain")]


# --- audit verdicts ---------------------------------------------------------

TOOL_RESULTS = [
    {"monthly_income": 85000.0, "monthly_surplus": 20862.0, "idle_balance": 125173.0,
     "savings_rate": 0.2454},
    {"products": [{"name": "FD Ladder", "min_amount": 10000, "expected_return": "7.4% p.a."}]},
]

PASS_TABLE = [
    "Your income is ₹85,000 a month.",
    "You save ₹20,862 monthly.",
    "₹21,000 is roughly your surplus.",           # nearest-thousand tolerance
    "About 1.25 lakh is idle.",                    # lakh-scale rounding of 125173
    "The FD earns 7.4% p.a.",                      # rate from a display string
    "Your savings rate is about 24.5%.",           # ratio 0.2454 → percent
    "आपकी मासिक आय ₹८५,००० है।",                    # Devanagari digits, same figure
    "You are 28 and have 2 goals for 2026.",       # small ints + year whitelisted
    "Support is available 24x7.",
    "The minimum is ₹10,000.",
]

FAIL_TABLE = [
    "You have ₹9,99,999 idle.",                    # invented amount
    "You could earn 15% easily.",                  # invented rate
    "Invest 2 lakh right away.",                   # invented lakh-scale amount
    "आपके पास ₹५,००,००० हैं।",                       # invented Devanagari amount
    "તમારી પાસે ₹૯,૯૯,૯૯૯ છે.",                     # invented Gujarati amount
    "You spent 543210 last month.",                # large bare int, unverified
    "Invest two crore right away.",                # invented spelled-out amount
    "बस 15 हज़ार लगा दो।",                          # invented digits+thousand form
    "पाँच लाख निवेश करो।",                          # invented spelled hi amount
]


@pytest.mark.parametrize("reply", PASS_TABLE)
def test_grounded_replies_pass(reply):
    assert g.audit_reply(reply, TOOL_RESULTS).ok, reply


@pytest.mark.parametrize("reply", FAIL_TABLE)
def test_hallucinated_replies_fail(reply):
    verdict = g.audit_reply(reply, TOOL_RESULTS)
    assert not verdict.ok, reply
    assert verdict.violations


def test_empty_reply_passes():
    assert g.audit_reply("", TOOL_RESULTS).ok
    assert g.audit_reply(None, TOOL_RESULTS).ok


def test_extra_figures_extend_allowed_set():
    verdict = g.audit_reply("Net worth ₹3,50,000.", [], extra=[{"total": 350000.0}])
    assert verdict.ok


def test_verdict_summary_shape():
    verdict = g.audit_reply("You have ₹9,99,999.", TOOL_RESULTS)
    summary = verdict.summary()
    assert summary["ok"] is False
    assert summary["violation_count"] == 1
    assert summary["violations"][0]["raw"] == "₹9,99,999"


def test_word_form_passes_when_cited():
    tools = [{"goal_target": 500000.0, "portfolio_total": 20000000.0}]
    assert g.audit_reply("आपका लक्ष्य पाँच लाख है।", tools).ok
    assert g.audit_reply("Your portfolio is two crore strong.", tools).ok


def test_scale_drift_blocked_at_one_lakh_cap():
    # devika-style: tools say ₹2.0Cr; a ₹2.1Cr claim (₹10L drift) must be
    # BLOCKED — the 2% relative tolerance is capped at ₹1,00,000 absolute.
    tools = [{"portfolio_total": 20000000.0}]
    assert not g.audit_reply("Your portfolio is ₹2.1 crore.", tools).ok
    assert not g.audit_reply("You hold about ₹2,10,00,000.", tools).ok
    assert g.audit_reply("Your portfolio is ₹2 crore.", tools).ok
    assert g.audit_reply("You hold ₹2,00,50,000.", tools).ok  # within the ₹1L cap


def test_format_inr_indian_grouping():
    assert g.format_inr(547386) == "5,47,386"
    assert g.format_inr(125173) == "1,25,173"
    assert g.format_inr(85000) == "85,000"
    assert g.format_inr(999) == "999"
    assert g.format_inr(20000000) == "2,00,00,000"
    assert g.format_inr(-125173) == "-1,25,173"


# --- safe template + stricter instruction ------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "gu"])
def test_safe_template_always_passes_guardrail(lang):
    figures = {"monthly_surplus": 20862.0, "idle_balance": 125173.0}
    text = g.safe_template(figures, lang)
    assert g.audit_reply(text, [figures]).ok


def test_stricter_instruction_names_violations_and_allowed():
    amounts, percents = g.build_allowed(TOOL_RESULTS)
    verdict = g.audit_numbers("You have ₹9,99,999.", amounts, percents)
    instruction = g.stricter_instruction(verdict, amounts, percents)
    assert "₹9,99,999" in instruction
    assert "₹85,000" in instruction
    assert "7.4%" in instruction


# --- BUG B: a guarantee/assured-return ask always gets an explicit refusal --


GUARANTEE_PHRASES = [
    "Can you guarantee me 20% returns if I invest right now?",
    "Can you guarantee me a 20 percent return?",
    "I want an assured return of 15%",
    "Will you promise me a fixed return on this?",
    "Can you double my money in a year?",
    "give me a risk-free high return option",
    "क्या आप गारंटी दे सकते हैं?",
]

NON_GUARANTEE_PHRASES = [
    "How is my spending this month?",
    "I want to invest my surplus",
    "What is a mutual fund?",
    "Can I get a personal loan?",
]


@pytest.mark.parametrize("text", GUARANTEE_PHRASES)
def test_is_guarantee_request_detects_guarantee_phrasing(text):
    assert g.is_guarantee_request(text)


@pytest.mark.parametrize("text", NON_GUARANTEE_PHRASES)
def test_is_guarantee_request_ignores_ordinary_turns(text):
    assert not g.is_guarantee_request(text)


def test_is_guarantee_request_handles_empty_text():
    assert not g.is_guarantee_request("")
    assert not g.is_guarantee_request(None)


@pytest.mark.parametrize("lang", ["en", "hi", "gu"])
def test_guarantee_refusal_template_always_passes_guardrail_and_refuses(lang):
    figures = {"monthly_surplus": 20862.0, "idle_balance": 125173.0}
    text = g.guarantee_refusal_template(figures, lang)
    assert g.audit_reply(text, [figures]).ok
    # never promises a return, and states the refusal plainly in each language
    assert "%" not in text
    if lang == "en":
        assert "no one can guarantee" in text.lower()
    elif lang == "hi":
        assert "गारंटी नहीं दे सकता" in text
    else:
        assert "ખાતરી આપી શકતું નથી" in text


def test_guarantee_regen_addendum_asks_the_model_to_refuse_not_repeat_the_number():
    assert "guarantee" in g.GUARANTEE_REGEN_ADDENDUM.lower()
    assert "unverified figure" in g.GUARANTEE_REGEN_ADDENDUM.lower()
