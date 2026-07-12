/**
 * Client-side i18n for the customer chat surface (`routes/customer/**`,
 * `components/chat/**`). Cheap, instant, in-memory — a plain keyed lookup,
 * no network round-trip, so flipping `language` re-renders every static UI
 * string immediately (CLAUDE.md §5 "linguistic democratization").
 *
 * Scope: UI chrome only (labels, tooltips, empty states, buttons). Free-form
 * LLM chat prose is out of scope here — the backend already generates new
 * turns in the selected `language` (see `useChatSession.sendMessage`); only
 * the fixed seeded greeting frames get a best-effort client-side flip
 * (`translateGreetingText` below), never a full re-translation of arbitrary
 * past replies.
 */
import type { LanguageCode } from "@/components/shared/LangToggle";

export type { LanguageCode };

type Entry = Record<LanguageCode, string>;

const DICT = {
  // -- header ---------------------------------------------------------
  "header.status.idle": { en: "Here to help", hi: "मदद के लिए तैयार", gu: "મદદ માટે તૈયાર" },
  "header.status.listening": { en: "Listening…", hi: "सुन रहा है…", gu: "સાંભળી રહ્યું છે…" },
  "header.status.thinking": { en: "Thinking…", hi: "सोच रहा है…", gu: "વિચારી રહ્યું છે…" },
  "header.status.speaking": { en: "Replying…", hi: "जवाब दे रहा है…", gu: "જવાબ આપી રહ્યું છે…" },
  "header.status.celebrating": { en: "Nice work!", hi: "शाबाश!", gu: "શાબાશ!" },
  "header.status.concerned": { en: "Here for you", hi: "आपके साथ हूं", gu: "તમારી સાથે છું" },
  "header.tab.chat": { en: "Chat", hi: "चैट", gu: "ચેટ" },
  "header.tab.dashboard": { en: "Dashboard", hi: "डैशबोर्ड", gu: "ડેશબોર્ડ" },
  "header.tooltip.switchPersona": { en: "Switch customer", hi: "ग्राहक बदलें", gu: "ગ્રાહક બદલો" },
  "header.tooltip.language": { en: "Change language", hi: "भाषा बदलें", gu: "ભાષા બદલો" },
  "header.tooltip.voiceOn": { en: "Turn off spoken replies", hi: "बोलकर जवाब बंद करें", gu: "બોલીને જવાબ બંધ કરો" },
  "header.tooltip.voiceOff": { en: "Turn on spoken replies", hi: "बोलकर जवाब चालू करें", gu: "બોલીને જવાબ ચાલુ કરો" },
  "header.tooltip.audit": {
    en: "See how this number was calculated",
    hi: "देखें यह आंकड़ा कैसे निकाला गया",
    gu: "આ આંકડો કેવી રીતે ગણાયો તે જુઓ",
  },
  "header.tooltip.chatTab": { en: "Back to the conversation", hi: "बातचीत पर वापस जाएं", gu: "વાતચીત પર પાછા જાઓ" },
  "header.tooltip.dashboardTab": {
    en: "Net worth, spending and goals",
    hi: "कुल संपत्ति, खर्च और लक्ष्य",
    gu: "કુલ સંપત્તિ, ખર્ચ અને લક્ષ્યો",
  },

  // -- language dropdown ------------------------------------------------
  "language.en": { en: "English", hi: "अंग्रेज़ी", gu: "અંગ્રેજી" },
  "language.hi": { en: "Hindi", hi: "हिंदी", gu: "હિન્દી" },
  "language.gu": { en: "Gujarati", hi: "गुजराती", gu: "ગુજરાતી" },

  // -- first-run icon tour ----------------------------------------------
  "tour.language.title": { en: "Change language anytime", hi: "कभी भी भाषा बदलें", gu: "ગમે ત્યારે ભાષા બદલો" },
  "tour.language.body": {
    en: "Switch between English, Hindi and Gujarati — the whole screen updates instantly.",
    hi: "अंग्रेज़ी, हिंदी और गुजराती के बीच बदलें — पूरी स्क्रीन तुरंत अपडेट होगी।",
    gu: "અંગ્રેજી, હિન્દી અને ગુજરાતી વચ્ચે બદલો — આખી સ્ક્રીન તરત જ અપડેટ થશે.",
  },
  "tour.voice.title": { en: "Hear your replies", hi: "अपने जवाब सुनें", gu: "તમારા જવાબ સાંભળો" },
  "tour.voice.body": {
    en: "Toggle spoken replies from your companion on or off.",
    hi: "अपने साथी के बोले गए जवाब चालू या बंद करें।",
    gu: "તમારા સાથીના બોલાયેલા જવાબ ચાલુ કે બંધ કરો.",
  },
  "tour.audit.title": { en: "Why this number", hi: "यह आंकड़ा क्यों", gu: "આ આંકડો શા માટે" },
  "tour.audit.body": {
    en: "Every figure WealthMitra shows you is computed from your data — tap here anytime to see the calculation trail.",
    hi: "WealthMitra जो भी आंकड़ा दिखाता है वह आपके डेटा से निकाला गया है — गणना का पूरा ब्योरा देखने के लिए कभी भी यहां टैप करें।",
    gu: "WealthMitra જે પણ આંકડો બતાવે છે તે તમારા ડેટા પરથી ગણવામાં આવ્યો છે — ગણતરીની વિગત જોવા માટે ગમે ત્યારે અહીં ટેપ કરો.",
  },
  "tour.dashboardTab.title": { en: "Your full picture", hi: "आपकी पूरी तस्वीर", gu: "તમારું સંપૂર્ણ ચિત્ર" },
  "tour.dashboardTab.body": {
    en: "See your net worth, spending, holdings and goals at a glance.",
    hi: "अपनी कुल संपत्ति, खर्च, निवेश और लक्ष्य एक नज़र में देखें।",
    gu: "તમારી કુલ સંપત્તિ, ખર્ચ, રોકાણ અને લક્ષ્યો એક નજરમાં જુઓ.",
  },
  "tour.step": { en: "Step {current} of {total}", hi: "चरण {current} / {total}", gu: "પગલું {current} / {total}" },
  "tour.skip": { en: "Skip", hi: "छोड़ें", gu: "છોડો" },
  "tour.next": { en: "Next", hi: "अगला", gu: "આગળ" },
  "tour.done": { en: "Got it", hi: "समझ गया", gu: "સમજાઈ ગયું" },

  // -- persona picker / switcher -----------------------------------------
  "persona.pickTitle": { en: "Who's chatting today?", hi: "आज कौन बात कर रहा है?", gu: "આજે કોણ વાત કરી રહ્યું છે?" },
  "persona.pickSubtitle": {
    en: "Pick a demo customer to start a WealthMitra conversation as them.",
    hi: "WealthMitra से बातचीत शुरू करने के लिए एक डेमो ग्राहक चुनें।",
    gu: "WealthMitra સાથે વાતચીત શરૂ કરવા માટે એક ડેમો ગ્રાહક પસંદ કરો.",
  },
  "persona.switchTitle": { en: "Switch customer", hi: "ग्राहक बदलें", gu: "ગ્રાહક બદલો" },
  "persona.switchSubtitle": {
    en: "Each customer keeps their own conversation — switch back anytime.",
    hi: "हर ग्राहक की बातचीत अलग से सुरक्षित रहती है — कभी भी वापस जाएं।",
    gu: "દરેક ગ્રાહકની વાતચીત અલગથી સચવાય છે — ગમે ત્યારે પાછા જાઓ.",
  },
  "persona.empty": { en: "No demo customers available", hi: "कोई डेमो ग्राहक उपलब्ध नहीं", gu: "કોઈ ડેમો ગ્રાહક ઉપલબ્ધ નથી" },
  "persona.emptyDesc": {
    en: "The persona roster couldn't be found for this session.",
    hi: "इस सत्र के लिए ग्राहक सूची नहीं मिल सकी।",
    gu: "આ સેશન માટે ગ્રાહક યાદી મળી શકી નથી.",
  },
  "persona.close": { en: "Close", hi: "बंद करें", gu: "બંધ કરો" },
  "persona.errorDesc": {
    en: "Couldn't load the customer roster. Try again.",
    hi: "ग्राहक सूची लोड नहीं हो सकी। फिर कोशिश करें।",
    gu: "ગ્રાહક યાદી લોડ થઈ શકી નથી. ફરી પ્રયાસ કરો.",
  },

  // -- persona switcher side panel (standalone /app only) -----------------
  "personaSwitcher.heading": { en: "Demo customers", hi: "डेमो ग्राहक", gu: "ડેમો ગ્રાહકો" },
  "personaSwitcher.subheading": {
    en: "Switch between customers — each keeps their own conversation.",
    hi: "ग्राहकों के बीच बदलें — हर एक की बातचीत अलग सुरक्षित रहती है।",
    gu: "ગ્રાહકો વચ્ચે બદલો — દરેકની વાતચીત અલગથી સચવાય છે.",
  },
  "personaSwitcher.active": { en: "Currently chatting", hi: "अभी बातचीत जारी है", gu: "હાલમાં વાતચીત ચાલુ છે" },

  // -- judge panel side panel (standalone /app only) -----------------------
  "judgePanel.eyebrow": { en: "For evaluators", hi: "मूल्यांकनकर्ताओं के लिए", gu: "મૂલ્યાંકનકર્તાઓ માટે" },
  "judgePanel.heading": { en: "Behind the scenes", hi: "पर्दे के पीछे", gu: "પડદા પાછળ" },
  "judgePanel.auditButton": { en: "View the audit trail", hi: "ऑडिट ट्रेल देखें", gu: "ઓડિટ ટ્રેલ જુઓ" },
  "judgePanel.auditDesc": {
    en: "See exactly how every number was computed — the compliance spine.",
    hi: "देखें हर आंकड़ा ठीक कैसे निकाला गया — यही है हमारी अनुपालन रीढ़।",
    gu: "જુઓ દરેક આંકડો બરાબર કેવી રીતે ગણાયો — આ જ છે અમારી અનુપાલન કરોડરજ્જુ.",
  },
  "judgePanel.auditWaiting": {
    en: "Starts a conversation first — then every step it took shows up here.",
    hi: "पहले बातचीत शुरू करें — फिर हर कदम यहां दिखेगा।",
    gu: "પહેલા વાતચીત શરૂ કરો — પછી દરેક પગલું અહીં દેખાશે.",
  },
  "judgePanel.rmButton": { en: "Open the RM Desk", hi: "आरएम डेस्क खोलें", gu: "આરએમ ડેસ્ક ખોલો" },
  "judgePanel.rmDescCalm": {
    en: "Leads you trigger in chat will appear here.",
    hi: "चैट में जो लीड आप बनाएंगे वे यहां दिखेंगी।",
    gu: "ચેટમાં તમે બનાવેલા લીડ અહીં દેખાશે.",
  },
  "judgePanel.rmDescActive": {
    en: "A lead was just routed — open the RM Desk to see it.",
    hi: "अभी एक लीड भेजी गई — उसे देखने के लिए आरएम डेस्क खोलें।",
    gu: "હમણાં જ એક લીડ મોકલવામાં આવી — તેને જોવા માટે આરએમ ડેસ્ક ખોલો.",
  },
  "judgePanel.leadCount": {
    en: "{count} lead in this space",
    hi: "इस स्पेस में {count} लीड",
    gu: "આ સ્પેસમાં {count} લીડ",
  },
  "judgePanel.note": {
    en: "These controls help you evaluate the system — a real customer never sees them.",
    hi: "ये नियंत्रण आपको सिस्टम जांचने में मदद करते हैं — असली ग्राहक इन्हें कभी नहीं देखता।",
    gu: "આ નિયંત્રણો તમને સિસ્ટમ ચકાસવામાં મદદ કરે છે — સાચો ગ્રાહક તેમને ક્યારેય જોતો નથી.",
  },

  // -- input --------------------------------------------------------------
  "input.placeholder": {
    en: "Ask about your money…",
    hi: "अपने पैसों के बारे में पूछें…",
    gu: "તમારા પૈસા વિશે પૂછો…",
  },
  "input.send": { en: "Send message", hi: "संदेश भेजें", gu: "સંદેશ મોકલો" },
  "input.micStart": { en: "Start voice input", hi: "आवाज़ से लिखना शुरू करें", gu: "અવાજથી લખવાનું શરૂ કરો" },
  "input.micStop": { en: "Stop voice input", hi: "आवाज़ से लिखना बंद करें", gu: "અવાજથી લખવાનું બંધ કરો" },

  // -- trust cue / audit drawer --------------------------------------------
  "trust.tooltip": {
    en: "Every figure here is computed from your data — tap the audit icon above to see the calculation trail.",
    hi: "यहां हर आंकड़ा आपके डेटा से निकाला गया है — गणना का पूरा ब्योरा देखने के लिए ऊपर ऑडिट आइकन टैप करें।",
    gu: "અહીં દરેક આંકડો તમારા ડેટા પરથી ગણવામાં આવ્યો છે — ગણતરીની વિગત જોવા માટે ઉપર ઓડિટ આઇકન ટેપ કરો.",
  },
  "trust.full": {
    en: "Every figure computed from your data · tap any number to see why",
    hi: "हर आंकड़ा आपके डेटा से निकाला गया है · किसी भी आंकड़े पर टैप करें",
    gu: "દરેક આંકડો તમારા ડેટા પરથી ગણવામાં આવ્યો છે · કોઈ પણ આંકડા પર ટેપ કરો",
  },
  "audit.title": { en: "Why this number", hi: "यह आंकड़ा क्यों", gu: "આ આંકડો શા માટે" },
  "audit.subtitle": {
    en: "Every tool call, reply, and check for this conversation",
    hi: "इस बातचीत की हर डेटा जांच, जवाब और सत्यापन",
    gu: "આ વાતચીતની દરેક ડેટા તપાસ, જવાબ અને ચકાસણી",
  },
  "audit.close": { en: "Close audit trail", hi: "ऑडिट ट्रेल बंद करें", gu: "ઓડિટ ટ્રેલ બંધ કરો" },
  "audit.empty": { en: "No audit entries yet", hi: "अभी कोई ऑडिट प्रविष्टि नहीं", gu: "હજુ કોઈ ઓડિટ એન્ટ્રી નથી" },
  "audit.emptyDesc": {
    en: "Ask WealthMitra something — every data lookup and decision will show up here.",
    hi: "WealthMitra से कुछ पूछें — हर डेटा लुकअप और फैसला यहां दिखेगा।",
    gu: "WealthMitra ને કંઈક પૂછો — દરેક ડેટા લુકઅપ અને નિર્ણય અહીં દેખાશે.",
  },
  "audit.errorDesc": {
    en: "Couldn't load the audit trail. Your data is unaffected — try again.",
    hi: "ऑडिट ट्रेल लोड नहीं हो सका। आपका डेटा सुरक्षित है — फिर कोशिश करें।",
    gu: "ઓડિટ ટ્રેલ લોડ ન થઈ શક્યું. તમારો ડેટા સુરક્ષિત છે — ફરી પ્રયાસ કરો.",
  },

  // -- chat error / retry ---------------------------------------------------
  "chat.errorBody": {
    en: "Something went wrong on our side. Nothing was changed — you can try again.",
    hi: "हमारी तरफ से कुछ गड़बड़ हुई। कुछ भी नहीं बदला — आप फिर कोशिश कर सकते हैं।",
    gu: "અમારા તરફથી કંઈક ખોટું થયું. કંઈ બદલાયું નથી — તમે ફરી પ્રયાસ કરી શકો છો.",
  },
  "chat.tryAgain": { en: "Try again", hi: "फिर कोशिश करें", gu: "ફરી પ્રયાસ કરો" },
  "chat.today": { en: "Today", hi: "आज", gu: "આજે" },
  "chat.couldNotStart": {
    en: "Couldn't start your conversation",
    hi: "आपकी बातचीत शुरू नहीं हो सकी",
    gu: "તમારી વાતચીત શરૂ થઈ શકી નથી",
  },
  "chat.couldNotStartDesc": {
    en: "WealthMitra couldn't reach the bank right now. Nothing was changed — try again.",
    hi: "WealthMitra अभी बैंक तक नहीं पहुंच सका। कुछ भी नहीं बदला — फिर कोशिश करें।",
    gu: "WealthMitra અત્યારે બેંક સુધી પહોંચી શક્યું નથી. કંઈ બદલાયું નથી — ફરી પ્રયાસ કરો.",
  },

  "dashboard.errorDesc": {
    en: "Couldn't load your dashboard right now. Your data is safe — try again.",
    hi: "अभी आपका डैशबोर्ड लोड नहीं हो सका। आपका डेटा सुरक्षित है — फिर कोशिश करें।",
    gu: "અત્યારે તમારું ડેશબોર્ડ લોડ થઈ શક્યું નથી. તમારો ડેટા સુરક્ષિત છે — ફરી પ્રયાસ કરો.",
  },

  // -- dashboard: net worth -------------------------------------------------
  "dashboard.netWorth.title": { en: "Total net worth", hi: "कुल संपत्ति", gu: "કુલ સંપત્તિ" },
  "dashboard.netWorth.reveal": { en: "Reveal net worth", hi: "कुल संपत्ति दिखाएं", gu: "કુલ સંપત્તિ બતાવો" },
  "dashboard.netWorth.hide": { en: "Hide net worth", hi: "कुल संपत्ति छिपाएं", gu: "કુલ સંપત્તિ છુપાવો" },
  "dashboard.netWorth.tapToReveal": { en: "Tap the eye to reveal", hi: "दिखाने के लिए आंख पर टैप करें", gu: "બતાવવા માટે આંખ પર ટેપ કરો" },
  "dashboard.netWorth.inBank": { en: "In the bank", hi: "बैंक में", gu: "બેંકમાં" },
  "dashboard.netWorth.outside": { en: "Outside accounts", hi: "बाहरी खाते", gu: "બહારના ખાતાં" },
  "dashboard.netWorth.notLinked": { en: "Not linked", hi: "लिंक नहीं है", gu: "લિંક નથી" },

  // -- dashboard: spend -----------------------------------------------------
  "dashboard.spend.eyebrow": { en: "Spend & cash flow", hi: "खर्च और नकदी प्रवाह", gu: "ખર્ચ અને રોકડ પ્રવાહ" },
  "dashboard.spend.title": { en: "Where your money moves", hi: "आपका पैसा कहां जाता है", gu: "તમારા પૈસા ક્યાં જાય છે" },
  "dashboard.spend.description": {
    en: "Monthly average, computed from your transaction ledger.",
    hi: "मासिक औसत, आपके लेनदेन से निकाला गया।",
    gu: "માસિક સરેરાશ, તમારા વ્યવહારો પરથી ગણેલ.",
  },
  "dashboard.spend.noSpend": { en: "No categorized spend yet.", hi: "अभी तक कोई वर्गीकृत खर्च नहीं।", gu: "હજુ સુધી કોઈ વર્ગીકૃત ખર્ચ નથી." },
  "dashboard.spend.cashflowTitle": { en: "This month's cash flow", hi: "इस महीने का नकदी प्रवाह", gu: "આ મહિનાનો રોકડ પ્રવાહ" },
  "dashboard.spend.income": { en: "Income", hi: "आय", gu: "આવક" },
  "dashboard.spend.spend": { en: "Spend", hi: "खर्च", gu: "ખર્ચ" },
  "dashboard.spend.surplus": { en: "Surplus", hi: "बचत", gu: "બચત" },
  "dashboard.spend.monthlySurplus": { en: "Monthly surplus", hi: "मासिक बचत", gu: "માસિક બચત" },

  // -- dashboard: holdings ----------------------------------------------------
  "dashboard.holdings.eyebrow": { en: "Holdings", hi: "निवेश", gu: "રોકાણ" },
  "dashboard.holdings.title": { en: "Your accounts", hi: "आपके खाते", gu: "તમારા ખાતાં" },
  "dashboard.holdings.description": {
    en: "Bank balance plus anything you've linked from outside IDBI.",
    hi: "बैंक बैलेंस के साथ IDBI के बाहर से जो कुछ भी आपने जोड़ा है।",
    gu: "IDBI બહારથી તમે લિંક કરેલ કંઈ પણ સાથે બેંક બેલેન્સ.",
  },
  "dashboard.holdings.bankBalance": { en: "Bank balance (IDBI)", hi: "बैंक बैलेंस (IDBI)", gu: "બેંક બેલેન્સ (IDBI)" },
  "dashboard.holdings.noneOnRecord": {
    en: "No external holdings or liabilities on record.",
    hi: "कोई बाहरी निवेश या देनदारी दर्ज नहीं है।",
    gu: "કોઈ બહારનું રોકાણ કે દેવું નોંધાયેલ નથી.",
  },
  "dashboard.holdings.shareOfConnected": {
    en: "{percent}% of connected holdings",
    hi: "जुड़े निवेश का {percent}%",
    gu: "જોડાયેલા રોકાણનું {percent}%",
  },

  // -- dashboard: AA connect --------------------------------------------------
  "dashboard.aa.linkTitle": { en: "Link your other accounts", hi: "अपने अन्य खाते जोड़ें", gu: "તમારા અન્ય ખાતાં લિંક કરો" },
  "dashboard.aa.linkDescription": {
    en: "See mutual funds, insurance, and pension held outside IDBI, right alongside your bank balance — pulled safely via the RBI Account Aggregator framework. Nothing is shared until you say so, and you can switch it off again at any time.",
    hi: "IDBI के बाहर रखे म्यूचुअल फंड, बीमा और पेंशन अपने बैंक बैलेंस के साथ देखें — RBI अकाउंट एग्रीगेटर फ्रेमवर्क के जरिए सुरक्षित रूप से लिया गया। जब तक आप न कहें, कुछ भी साझा नहीं होगा, और आप इसे कभी भी बंद कर सकते हैं।",
    gu: "IDBI બહાર રાખેલા મ્યુચ્યુઅલ ફંડ, વીમો અને પેન્શન તમારા બેંક બેલેન્સ સાથે જુઓ — RBI એકાઉન્ટ એગ્રીગેટર ફ્રેમવર્ક દ્વારા સુરક્ષિત રીતે લેવાયેલ. તમે કહો નહીં ત્યાં સુધી કંઈ શેર થશે નહીં, અને તમે તેને ગમે ત્યારે બંધ કરી શકો છો.",
  },
  "dashboard.aa.linkButton": { en: "Link external accounts", hi: "बाहरी खाते जोड़ें", gu: "બહારના ખાતાં લિંક કરો" },
  "dashboard.aa.requestingTransfer": {
    en: "Requesting transfer consent…",
    hi: "ट्रांसफर सहमति मांगी जा रही है…",
    gu: "ટ્રાન્સફર સંમતિ માંગવામાં આવી રહી છે…",
  },
  "dashboard.aa.requestingProcessing": {
    en: "Requesting processing consent…",
    hi: "प्रोसेसिंग सहमति मांगी जा रही है…",
    gu: "પ્રોસેસિંગ સંમતિ માંગવામાં આવી રહી છે…",
  },
  "dashboard.aa.transferLabel": {
    en: "Data transfer (Account Aggregator)",
    hi: "डेटा ट्रांसफर (अकाउंट एग्रीगेटर)",
    gu: "ડેટા ટ્રાન્સફર (એકાઉન્ટ એગ્રીગેટર)",
  },
  "dashboard.aa.transferDescription": {
    en: "Authorises pulling your external holdings via the AA network. This alone does not let WealthMitra use the data.",
    hi: "AA नेटवर्क के जरिए आपके बाहरी निवेश लाने की अनुमति देता है। इससे WealthMitra को डेटा इस्तेमाल करने की अनुमति नहीं मिलती।",
    gu: "AA નેટવર્ક દ્વારા તમારા બહારના રોકાણો લાવવાની પરવાનગી આપે છે. આનાથી WealthMitra ને ડેટા વાપરવાની પરવાનગી મળતી નથી.",
  },
  "dashboard.aa.processingLabel": { en: "Processing consent (DPDP)", hi: "प्रोसेसिंग सहमति (DPDP)", gu: "પ્રોસેસિંગ સંમતિ (DPDP)" },
  "dashboard.aa.processingDescription": {
    en: "Separately authorises WealthMitra to use that transferred data for your advisory dashboard.",
    hi: "यह अलग से WealthMitra को आपके डैशबोर्ड के लिए ट्रांसफर किए गए डेटा का इस्तेमाल करने की अनुमति देता है।",
    gu: "આ અલગથી WealthMitra ને તમારા ડેશબોર્ડ માટે ટ્રાન્સફર થયેલ ડેટા વાપરવાની પરવાનગી આપે છે.",
  },
  "dashboard.aa.discovering": {
    en: "Discovering your external accounts…",
    hi: "आपके बाहरी खाते खोजे जा रहे हैं…",
    gu: "તમારા બહારના ખાતાં શોધાઈ રહ્યાં છે…",
  },
  "dashboard.aa.linkedVia": { en: "Linked via Account Aggregator", hi: "अकाउंट एग्रीगेटर के जरिए जोड़ा गया", gu: "એકાઉન્ટ એગ્રીગેટર દ્વારા લિંક થયેલ" },
  "dashboard.aa.noneTitle": { en: "No external accounts detected", hi: "कोई बाहरी खाता नहीं मिला", gu: "કોઈ બહારનું ખાતું મળ્યું નથી" },
  "dashboard.aa.noneDescription": {
    en: "We haven't found any Account Aggregator-linkable investments, insurance, or pension accounts for this profile yet. Once you open one elsewhere, it'll show up here to link.",
    hi: "हमें इस प्रोफ़ाइल के लिए अभी तक कोई अकाउंट एग्रीगेटर-लिंक करने योग्य निवेश, बीमा या पेंशन खाता नहीं मिला है। जब आप कहीं और खाता खोलेंगे, तो वह यहां जोड़ने के लिए दिखेगा।",
    gu: "અમને આ પ્રોફાઇલ માટે હજુ સુધી કોઈ એકાઉન્ટ એગ્રીગેટર-લિંક કરી શકાય તેવું રોકાણ, વીમો કે પેન્શન ખાતું મળ્યું નથી. તમે ક્યાંક બીજે ખાતું ખોલશો ત્યારે તે અહીં લિંક કરવા દેખાશે.",
  },

  // -- dashboard: goals ---------------------------------------------------------
  "dashboard.goals.eyebrow": { en: "Goals", hi: "लक्ष्य", gu: "લક્ષ્યો" },
  "dashboard.goals.title": { en: "What you're saving for", hi: "आप किसके लिए बचत कर रहे हैं", gu: "તમે શેના માટે બચત કરી રહ્યાં છો" },
  "dashboard.goals.empty": { en: "No goals set yet", hi: "अभी कोई लक्ष्य नहीं है", gu: "હજુ કોઈ લક્ષ્ય નથી" },
  "dashboard.goals.emptyDesc": {
    en: "Goals you set in chat will show their progress here.",
    hi: "चैट में सेट किए गए लक्ष्यों की प्रगति यहां दिखेगी।",
    gu: "ચેટમાં સેટ કરેલા લક્ષ્યોની પ્રગતિ અહીં દેખાશે.",
  },
  "dashboard.goals.horizon": { en: "{years}-year horizon", hi: "{years}-वर्ष की अवधि", gu: "{years}-વર્ષની અવધિ" },
  "dashboard.goals.progress": { en: "{saved} of {target}", hi: "{target} में से {saved}", gu: "{target} માંથી {saved}" },
  "dashboard.goals.need": { en: "need {amount}/mo", hi: "{amount}/माह चाहिए", gu: "{amount}/મહિને જરૂરી" },

  // -- dashboard: nudges ----------------------------------------------------------
  "dashboard.nudges.eyebrow": { en: "For you", hi: "आपके लिए", gu: "તમારા માટે" },
  "dashboard.nudges.title": { en: "Nudges", hi: "सुझाव", gu: "સૂચનો" },
  "dashboard.nudges.empty": { en: "No nudges today", hi: "आज कोई सुझाव नहीं", gu: "આજે કોઈ સૂચન નથી" },
  "dashboard.nudges.emptyDesc": {
    en: "WealthMitra checks in when something worth acting on shows up in your data.",
    hi: "जब आपके डेटा में कुछ महत्वपूर्ण दिखे, तो WealthMitra आपसे संपर्क करेगा।",
    gu: "તમારા ડેટામાં કંઈક મહત્વનું દેખાય ત્યારે WealthMitra તમારો સંપર્ક કરશે.",
  },
  "dashboard.nudges.functionalLabel": { en: "Nudge", hi: "सुझाव", gu: "સૂચન" },
  "dashboard.nudges.relationalLabel": { en: "Check-in", hi: "जांच", gu: "ચેક-ઇન" },

  // -- default seed nudges (tool-grounded: amounts come from real metrics) -------
  "nudge.idle.title": { en: "{amount} sitting idle", hi: "{amount} बचत में बेकार पड़ा है", gu: "{amount} બચતમાં નવરું પડ્યું છે" },
  "nudge.idle.body": {
    en: "That's parked in your savings account — a good candidate to put to work.",
    hi: "यह आपके बचत खाते में बेकार पड़ा है — इसे काम पर लगाने पर विचार करें।",
    gu: "આ તમારા બચત ખાતામાં નવરું પડ્યું છે — તેને કામે લગાડવાનું વિચારો.",
  },
  "nudge.surplus.title": {
    en: "{amount}/mo surplus to put to work",
    hi: "{amount}/माह की बचत निवेश के लिए तैयार",
    gu: "{amount}/મહિને બચત રોકાણ માટે તૈયાર",
  },
  "nudge.surplus.body": {
    en: "Consider directing part of it toward your goals.",
    hi: "इसका कुछ हिस्सा अपने लक्ष्यों की ओर लगाने पर विचार करें।",
    gu: "તેનો થોડો ભાગ તમારા લક્ષ્યો તરફ વાળવાનું વિચારો.",
  },
  "nudge.sip.title": { en: "SIP due soon", hi: "SIP जल्द देय है", gu: "SIP ટૂંક સમયમાં ડ્યૂ છે" },
  "nudge.sip.body": {
    en: "Your monthly SIP is coming up — make sure funds are ready.",
    hi: "आपकी मासिक SIP आने वाली है — सुनिश्चित करें कि पैसे तैयार हैं।",
    gu: "તમારી માસિક SIP આવી રહી છે — ખાતરી કરો કે ફંડ તૈયાર છે.",
  },
  "nudge.tax.title": { en: "Tax-saving window open", hi: "टैक्स-बचत की समय-सीमा खुली है", gu: "ટેક્સ-બચતની વિન્ડો ખુલ્લી છે" },
  "nudge.tax.body": {
    en: "Section 80C options can still lower this year's tax bill.",
    hi: "80C के विकल्प अब भी इस साल का टैक्स कम कर सकते हैं।",
    gu: "80C વિકલ્પો હજુ પણ આ વર્ષનો ટેક્સ ઘટાડી શકે છે.",
  },
  "nudge.literacy.title": { en: "Know your safety net", hi: "अपना सुरक्षा कवच जानें", gu: "તમારું સુરક્ષા કવચ જાણો" },
  "nudge.literacy.body": {
    en: "A 3–6 month expense buffer keeps surprises from becoming setbacks.",
    hi: "3–6 महीने का खर्च बफर अचानक झटकों से बचाता है।",
    gu: "3–6 મહિનાનો ખર્ચ બફર અચાનક આંચકાઓથી બચાવે છે.",
  },
} satisfies Record<string, Entry>;

export type TKey = keyof typeof DICT;

/** Interpolates `{name}` placeholders in a translated template with `vars`. */
export function t(language: LanguageCode, key: TKey, vars?: Record<string, string | number>): string {
  const entry = DICT[key];
  const template = entry[language] ?? entry.en;
  if (!vars) return template;
  return Object.entries(vars).reduce(
    (acc, [name, value]) => acc.replaceAll(`{${name}}`, String(value)),
    template
  );
}

/** Bound translator for a fixed language — avoids passing `language` at every call site. */
export function makeT(language: LanguageCode) {
  return (key: TKey, vars?: Record<string, string | number>) => t(language, key, vars);
}
