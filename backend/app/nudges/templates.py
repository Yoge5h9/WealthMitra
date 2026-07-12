"""Deterministic i18n nudge copy (en/hi/gu) — the guardrail-safe fallback for
every `template_id` a trigger in `triggers.py` can emit, and the grounding
reference the LLM is asked to rephrase (`engine.py`). Every figure here comes
straight from the candidate's `facts` dict; nothing is invented.
"""

from __future__ import annotations

from collections.abc import Callable

from app.agent.guardrails import format_inr

Render = Callable[[dict], tuple[str, str]]


def _inr(value: float | int) -> str:
    return format_inr(float(value))


def _pct(value: float) -> str:
    # facts may carry a ratio (0..1) or an already-scaled percent; normalise.
    v = float(value)
    if 0 < v < 1:
        v *= 100
    return f"{v:.1f}".rstrip("0").rstrip(".")


_CATEGORY_LABELS = {
    "food": {"en": "food & dining", "hi": "खाने-पीने", "gu": "ખાવા-પીવા"},
    "shopping": {"en": "shopping", "hi": "शॉपिंग", "gu": "શોપિંગ"},
    "travel": {"en": "travel", "hi": "यात्रा", "gu": "મુસાફરી"},
    "entertainment": {"en": "entertainment", "hi": "मनोरंजन", "gu": "મનોરંજન"},
    "utilities": {"en": "utilities", "hi": "यूटिलिटी बिल", "gu": "યુટિલિટી બિલ"},
}


def _category_label(category: str, language: str) -> str:
    entry = _CATEGORY_LABELS.get(category)
    if entry:
        return entry.get(language, entry["en"])
    return category.replace("_", " ")


def _tpl(en: Render, hi: Render, gu: Render) -> dict[str, Render]:
    return {"en": en, "hi": hi, "gu": gu}


_TEMPLATES: dict[str, dict[str, Render]] = {
    "idle_balance_high": _tpl(
        lambda f: ("Idle cash could work harder",
                    f"You have ₹{_inr(f['idle_balance'])} sitting idle — more than double your monthly "
                    f"surplus of ₹{_inr(f['monthly_surplus'])}. Consider moving some into an investment."),
        lambda f: ("पड़ी हुई रकम को काम पर लगाएँ",
                    f"आपके खाते में ₹{_inr(f['idle_balance'])} पड़े हैं — आपकी मासिक बचत ₹{_inr(f['monthly_surplus'])} "
                    "से दोगुने से भी ज़्यादा। इसमें से कुछ निवेश करने पर विचार करें।"),
        lambda f: ("પડેલી રકમને કામે લગાડો",
                    f"તમારા ખાતામાં ₹{_inr(f['idle_balance'])} પડ્યા છે — તમારી માસિક બચત ₹{_inr(f['monthly_surplus'])} "
                    "કરતાં બમણાથી વધુ. તેમાંથી થોડું રોકાણ કરવાનું વિચારો."),
    ),
    "sip_due": _tpl(
        lambda f: ("Your salary just landed — put your surplus to work",
                    f"With a monthly surplus of ₹{_inr(f['monthly_surplus'])}, a regular SIP right after "
                    "salary day is one of the simplest ways to build wealth consistently."),
        lambda f: ("सैलरी आ गई — अपनी बचत को निवेश में लगाएँ",
                    f"आपकी मासिक बचत ₹{_inr(f['monthly_surplus'])} है — सैलरी आने के तुरंत बाद एक नियमित SIP "
                    "शुरू करना लगातार पैसा बढ़ाने का सबसे आसान तरीका है।"),
        lambda f: ("પગાર આવી ગયો — તમારી બચતને રોકાણમાં લગાડો",
                    f"તમારી માસિક બચત ₹{_inr(f['monthly_surplus'])} છે — પગાર પછી તરત નિયમિત SIP શરૂ કરવું "
                    "એ સતત સંપત્તિ વધારવાની સૌથી સરળ રીત છે."),
    ),
    "goal_drift": _tpl(
        lambda f: (f"'{f['goal_name']}' needs a top-up",
                    f"You're at {_pct(f['progress_ratio'])}% of your '{f['goal_name']}' goal. Saving around "
                    f"₹{_inr(f['monthly_required_inr'])} a month from here keeps you on track."),
        lambda f: (f"'{f['goal_name']}' पर ध्यान दें",
                    f"आप अपने '{f['goal_name']}' लक्ष्य का {_pct(f['progress_ratio'])}% पूरा कर चुके हैं। यहाँ से "
                    f"लगभग ₹{_inr(f['monthly_required_inr'])} प्रति माह बचाने से आप लक्ष्य तक पहुँच सकते हैं।"),
        lambda f: (f"'{f['goal_name']}' પર ધ્યાન આપો",
                    f"તમે તમારા '{f['goal_name']}' ધ્યેયનું {_pct(f['progress_ratio'])}% પૂરું કર્યું છે. અહીંથી "
                    f"દર મહિને લગભગ ₹{_inr(f['monthly_required_inr'])} બચાવવાથી તમે ધ્યેય સુધી પહોંચી શકશો."),
    ),
    "tax_window": _tpl(
        lambda f: ("Tax-saving window is open",
                    "This financial year's tax-saving investment window closes soon — it's a good time to "
                    "review your options before it shuts."),
        lambda f: ("टैक्स-बचत का समय चल रहा है",
                    "इस वित्तीय वर्ष की टैक्स-बचत निवेश की खिड़की जल्द बंद हो रही है — अभी अपने विकल्पों की "
                    "समीक्षा करने का अच्छा समय है।"),
        lambda f: ("ટેક્સ-બચતનો સમય ચાલુ છે",
                    "આ નાણાકીય વર્ષની ટેક્સ-બચત રોકાણની તક ટૂંક સમયમાં પૂરી થઈ રહી છે — હમણાં તમારા "
                    "વિકલ્પો તપાસવાનો સારો સમય છે."),
    ),
    "fd_maturity": _tpl(
        lambda f: ("A fixed deposit is nearing maturity",
                    f"Your FD with {f['institution']} (₹{_inr(f['amount'])}) is coming up for renewal — "
                    "worth comparing rates before it auto-renews."),
        lambda f: ("एक फिक्स्ड डिपॉज़िट मैच्योर होने वाली है",
                    f"{f['institution']} में आपकी ₹{_inr(f['amount'])} की FD मैच्योर होने वाली है — रिन्यू होने "
                    "से पहले दरों की तुलना करना फ़ायदेमंद रहेगा।"),
        lambda f: ("એક ફિક્સ્ડ ડિપોઝિટ પાકવાની તૈયારીમાં છે",
                    f"{f['institution']} ખાતેની તમારી ₹{_inr(f['amount'])} ની FD પાકવાની છે — રિન્યુ થાય "
                    "તે પહેલાં દરોની સરખામણી કરવી ફાયદાકારક રહેશે."),
    ),
    "external_refinance": _tpl(
        lambda f: ("An out-of-bank opportunity worth a look",
                    f"Comparing your external holdings and loans against today's rates could be worth "
                    f"about ₹{_inr(f['estimated_annual_impact_inr'])} a year — worth a specialist review."),
        lambda f: ("बाहर के निवेश/लोन पर एक मौका",
                    f"आपके बाहरी निवेश और लोन की आज की दरों से तुलना करने पर सालाना लगभग "
                    f"₹{_inr(f['estimated_annual_impact_inr'])} की बचत हो सकती है — विशेषज्ञ से जाँच कराना ठीक रहेगा।"),
        lambda f: ("બહારના રોકાણ/લોન પર એક તક",
                    f"તમારા બહારના રોકાણ અને લોનની આજના દર સાથે સરખામણી કરવાથી વર્ષે લગભગ "
                    f"₹{_inr(f['estimated_annual_impact_inr'])} ની બચત થઈ શકે — નિષ્ણાત પાસે તપાસ કરાવવી સારું રહેશે."),
    ),
    "overspend_vs_baseline": _tpl(
        lambda f: (f"{f['category'].replace('_', ' ').title()} spend jumped this month",
                    f"You spent ₹{_inr(f['current_month_spend'])} on {f['category'].replace('_', ' ')} this "
                    f"month, versus a usual ₹{_inr(f['baseline_spend'])}. Worth a quick look."),
        lambda f: ("इस महीने खर्च बढ़ा",
                    f"इस महीने आपने ₹{_inr(f['current_month_spend'])} खर्च किए, जबकि सामान्य महीने में यह "
                    f"₹{_inr(f['baseline_spend'])} होता है। एक बार देख लें।"),
        lambda f: ("આ મહિને ખર્ચ વધ્યો",
                    f"આ મહિને તમે ₹{_inr(f['current_month_spend'])} ખર્ચ કર્યા, જ્યારે સામાન્ય રીતે તે "
                    f"₹{_inr(f['baseline_spend'])} હોય છે. એકવાર જોઈ લો."),
    ),
    "emi_stress_protective": _tpl(
        lambda f: ("Let's find you some breathing room",
                    f"Your EMIs are taking up a large share of your income right now, on a surplus of "
                    f"₹{_inr(f['monthly_surplus'])}. Let's review your cash-flow together — no pressure, no products."),
        lambda f: ("आपके लिए थोड़ी राहत ढूँढते हैं",
                    f"अभी आपकी EMI आपकी आय का बड़ा हिस्सा ले रही है, जबकि बचत ₹{_inr(f['monthly_surplus'])} है। "
                    "आइए मिलकर आपके कैश-फ्लो को देखें — कोई दबाव नहीं, कोई प्रोडक्ट नहीं।"),
        lambda f: ("તમારા માટે થોડી રાહત શોધીએ",
                    f"અત્યારે તમારી EMI તમારી આવકનો મોટો ભાગ લઈ રહી છે, જ્યારે બચત ₹{_inr(f['monthly_surplus'])} છે. "
                    "ચાલો સાથે મળીને તમારો કેશ-ફ્લો જોઈએ — કોઈ દબાણ નહીં, કોઈ પ્રોડક્ટ નહીં."),
    ),
    "monthly_money_story": _tpl(
        lambda f: ("Your month in money",
                    f"You brought in ₹{_inr(f['monthly_income'])} and saved ₹{_inr(f['monthly_surplus'])} "
                    f"({_pct(f['savings_rate'])}% of income) — {_category_label(f['top_category'], 'en')} was "
                    "your biggest spend."),
        lambda f: ("इस महीने आपका पैसा",
                    f"आपकी आय ₹{_inr(f['monthly_income'])} रही और आपने ₹{_inr(f['monthly_surplus'])} "
                    f"({_pct(f['savings_rate'])}% आय) बचाए — सबसे ज़्यादा खर्च {_category_label(f['top_category'], 'hi')} पर हुआ।"),
        lambda f: ("આ મહિને તમારા પૈસાની વાર્તા",
                    f"તમારી આવક ₹{_inr(f['monthly_income'])} રહી અને તમે ₹{_inr(f['monthly_surplus'])} "
                    f"({_pct(f['savings_rate'])}% આવક) બચાવ્યા — સૌથી વધુ ખર્ચ {_category_label(f['top_category'], 'gu')} પર થયો."),
    ),
    "goal_celebration": _tpl(
        lambda f: (f"Great progress on '{f['goal_name']}'!",
                    f"You've reached {_pct(f['progress_ratio'])}% of your '{f['goal_name']}' goal — keep it up, "
                    "you're most of the way there."),
        lambda f: (f"'{f['goal_name']}' में शानदार प्रगति!",
                    f"आपने अपने '{f['goal_name']}' लक्ष्य का {_pct(f['progress_ratio'])}% पूरा कर लिया है — ऐसे ही "
                    "बढ़ते रहें, आप मंज़िल के करीब हैं।"),
        lambda f: (f"'{f['goal_name']}' માં શાનદાર પ્રગતિ!",
                    f"તમે તમારા '{f['goal_name']}' ધ્યેયનું {_pct(f['progress_ratio'])}% પૂરું કર્યું છે — આમ જ "
                    "આગળ વધો, તમે લક્ષ્યની નજીક છો."),
    ),
    "literacy_emergency_fund": _tpl(
        lambda f: ("Why an emergency fund matters",
                    "A cushion of 3-6 months' expenses, kept liquid, means a surprise bill or income gap "
                    "never has to become a crisis."),
        lambda f: ("इमरजेंसी फंड क्यों ज़रूरी है",
                    "3-6 महीने के खर्च जितनी रकम आसानी से निकाली जा सके ऐसी जगह रखने से अचानक आया खर्च या "
                    "आय में कमी संकट नहीं बनती।"),
        lambda f: ("ઇમરજન્સી ફંડ કેમ મહત્વનું છે",
                    "3-6 મહિનાના ખર્ચ જેટલી રકમ સહેલાઈથી ઉપાડી શકાય તેવી જગ્યાએ રાખવાથી અચાનક ખર્ચ કે "
                    "આવકમાં ઘટાડો કટોકટી નથી બનતો."),
    ),
    "literacy_power_of_sip": _tpl(
        lambda f: ("The power of starting early",
                    "A SIP invests a fixed amount every month, buying more units when prices dip and fewer "
                    "when they rise — small, regular amounts compound meaningfully over years."),
        lambda f: ("जल्दी शुरू करने की ताक़त",
                    "SIP में हर महीने एक तय रकम निवेश होती है — दाम कम होने पर ज़्यादा यूनिट, ज़्यादा होने पर कम। "
                    "छोटी, नियमित रकम सालों में अच्छा असर दिखाती है।"),
        lambda f: ("વહેલા શરૂ કરવાની તાકાત",
                    "SIP માં દર મહિને નિશ્ચિત રકમનું રોકાણ થાય છે — ભાવ ઓછો હોય ત્યારે વધુ યુનિટ, વધુ હોય ત્યારે ઓછા. "
                    "નાની, નિયમિત રકમ વર્ષોમાં સારું પરિણામ આપે છે."),
    ),
    "literacy_diversification": _tpl(
        lambda f: ("Don't put all your eggs in one basket",
                    "Spreading money across different kinds of assets means one bad patch in a single "
                    "investment doesn't derail your whole plan."),
        lambda f: ("सारे अंडे एक टोकरी में मत रखिए",
                    "पैसे को अलग-अलग तरह के निवेशों में बाँटने से किसी एक निवेश में गिरावट पूरी योजना को "
                    "नुकसान नहीं पहुँचाती।"),
        lambda f: ("બધા ઈંડા એક ટોપલીમાં ન રાખો",
                    "પૈસાને જુદા જુદા પ્રકારના રોકાણોમાં વહેંચવાથી કોઈ એક રોકાણમાં ઘટાડો આખી યોજનાને "
                    "નુકસાન નથી પહોંચાડતો."),
    ),
    "literacy_credit_score": _tpl(
        lambda f: ("Your credit score, in plain terms",
                    "Paying bills and EMIs on time, and not maxing out credit limits, are the two biggest "
                    "levers for a healthy credit score."),
        lambda f: ("आपका क्रेडिट स्कोर, आसान भाषा में",
                    "समय पर बिल और EMI चुकाना, और क्रेडिट लिमिट को पूरी तरह इस्तेमाल न करना — ये दो सबसे बड़े "
                    "कारक हैं एक अच्छे क्रेडिट स्कोर के लिए।"),
        lambda f: ("તમારો ક્રેડિટ સ્કોર, સાદી ભાષામાં",
                    "સમયસર બિલ અને EMI ભરવા, અને ક્રેડિટ લિમિટનો પૂરો ઉપયોગ ન કરવો — આ બે સૌથી મોટા "
                    "પરિબળો છે સારા ક્રેડિટ સ્કોર માટે."),
    ),
    "diwali_budgeting": _tpl(
        lambda f: ("Planning your festive budget",
                    "Festive season spending adds up fast — setting a Diwali budget ahead of time helps you "
                    "enjoy it without a January surprise."),
        lambda f: ("त्योहारी बजट की योजना",
                    "त्योहारी सीज़न में खर्च तेज़ी से बढ़ता है — पहले से दिवाली का बजट तय करने से बिना किसी "
                    "जनवरी के झटके के त्योहार मनाया जा सकता है।"),
        lambda f: ("તહેવારના બજેટનું આયોજન",
                    "તહેવારોની સિઝનમાં ખર્ચ ઝડપથી વધે છે — અગાઉથી દિવાળીનું બજેટ નક્કી કરવાથી જાન્યુઆરીના "
                    "આંચકા વગર તહેવાર ઉજવી શકાય."),
    ),
    "new_year_planning": _tpl(
        lambda f: ("A fresh financial year, a fresh plan",
                    "The turn of the year is a natural checkpoint — a good time to revisit your goals and "
                    "see if your savings plan still fits them."),
        lambda f: ("नया साल, नई वित्तीय योजना",
                    "साल का बदलना एक अच्छा पड़ाव है — अपने लक्ष्यों को फिर से देखने और यह जाँचने का कि आपकी "
                    "बचत योजना अब भी सही है या नहीं।"),
        lambda f: ("નવું વર્ષ, નવી નાણાકીય યોજના",
                    "વર્ષ બદલાવું એ એક સારો પડાવ છે — તમારા ધ્યેયો ફરી તપાસવાનો અને તમારી બચત યોજના હજુ "
                    "બંધબેસે છે કે નહીં તે જોવાનો સારો સમય."),
    ),
    "independence_savings_pledge": _tpl(
        lambda f: ("A small savings pledge this August",
                    "Mid-August is a nice moment to make one small, concrete savings commitment for the "
                    "rest of the year."),
        lambda f: ("इस अगस्त एक छोटी बचत प्रतिज्ञा",
                    "अगस्त के मध्य में साल के बचे हिस्से के लिए एक छोटा, ठोस बचत संकल्प लेने का अच्छा मौका है।"),
        lambda f: ("આ ઓગસ્ટમાં એક નાની બચત પ્રતિજ્ઞા",
                    "ઓગસ્ટના મધ્યમાં વર્ષના બાકીના ભાગ માટે એક નાનું, નક્કર બચત વચન લેવાનો સારો સમય છે."),
    ),
}


def render(template_id: str, language: str, facts: dict) -> tuple[str, str]:
    """Render `template_id` in `language` from `facts`. Falls back to English
    if the language isn't covered; raises `KeyError` for an unknown template
    id (a programming error in a trigger, not a runtime data condition).
    """
    entry = _TEMPLATES[template_id]
    fn = entry.get(language, entry["en"])
    return fn(facts)


__all__ = ["render"]
