# WealthMitra (धन मित्र)

**IDBI Innovate 2026 · Track 01 · Wealth Advisory / Conversational AI / Mobile Banking**
Team **404 Sleep Not Found**

Wealth advisory in India is human-gated: a relationship manager calls you if your
balance is big enough — everyone else gets generic banners. WealthMitra is a
vernacular, AI wealth **companion** embedded in the bank's mobile app. It reads a
customer's real transaction behaviour and out-of-bank holdings and turns them into
personalized, data-grounded guidance. Simple products execute instantly; regulated
products convert into structured, high-context leads for a human Relationship Manager.

**We are a companion, not an adviser.** SEBI reserves "Adviser / Wealth Manager" for
Registered Investment Advisers. WealthMitra does information and distribution —
factual, data-grounded, in the customer's own language. A personalised,
suitability-driven recommendation on a regulated product belongs to the human RM
path, always. That line isn't branding — it's what lets an AI companion operate at
bank scale without stepping into regulated advisory territory.

## What it does

- **360° financial picture, inside the bank app.** One view of internal accounts and
  cards and — once the customer explicitly connects via Account Aggregator — out-of-bank
  mutual funds, equity, insurance, and NPS. Net-worth, cash-flow, and spend breakdowns
  are computed from real data, never guessed.
- **New to the bank? Start with a conversation.** A customer with no history answers
  four quick questions; WealthMitra builds a starting profile, shows a clear money
  picture right away, and — with explicit consent — links external accounts via Account
  Aggregator to complete it. Onboarding into advisory in one flow, no paperwork.
- **Grounded conversation in English / हिंदी / ગુજરાતી.** Ask anything about your money —
  every number in the reply traces to a real calculation, never a guessed figure.
  Switch language mid-conversation; the companion's voice stays the same.
- **A real IDBI product shelf.** FDs (incl. senior / Chiranjeevi / Suvidha-tax),
  PPF/SSY/SCSS/NPS/RBI bonds, direct-plan mutual funds, credit cards (Aspire / Euphoria /
  Imperium), Ageas Federal / Niva Bupa / Tata AIG insurance, PMS/AIF via IDBI Capital,
  and NRE/NRO/FCNR accounts — with published eligibility, not invented terms.
- **Vanilla products execute instantly.** A plain SIP, RD, or retail FD is confirmed
  live with a receipt — no human in the loop, because nothing here is regulated advice.
- **Regulated asks reach a human RM, live.** Ask about equity, ULIPs, PMS/AIF, or
  anything suitability-driven, and a structured **Lead Packet** (goals, risk score,
  suitability profile) lands on the RM's desk in real time. This boundary is enforced in
  code, not by a prompt.
- **Distress suppresses selling.** When EMIs eat too much of a customer's income, every
  product nudge is suppressed and the companion routes to debt-help and financial
  literacy only. It's on the customer's side first.
- **Proactive nudges & literacy.** Idle-balance-to-invest, SIP-due, goal-drift, and
  tax-saving-window nudges, delivered as push / SMS / WhatsApp / voice-call variants of
  the same grounded message.
- **Persona-aware communication.** The same companion adapts tone and format to who it's
  speaking with — short mobile-first actions for a busy salaried customer, patient
  voice-friendly steps for a senior, async time-zone-aware messages for an NRI — without
  changing any figure or compliance rule.

## What's real vs pre-seeded vs simulated

We say this up front in the app itself; here it is for anyone evaluating the product.

| Layer | Status | Note |
|---|---|---|
| Chat answers (AI agent) | **REAL** — live, grounded in calculations | Type anything, get a real grounded reply |
| All figures (spend, cash-flow, net-worth, two-axis risk, suitability segment) | **REAL, deterministic** | The "compute the numbers" spine |
| Routing (vanilla-auto vs RM-lead vs distress-suppress) | **REAL, deterministic** | Fully test-covered — the compliance core |
| Suitability product filtering | **REAL, deterministic (config-driven)** | Governance & scalability |
| 3-surface live sync (chat → RM queue → nudge) | **REAL** | Everything updates in real time |
| Nudge copy, RM lead narrative, multilingual replies | **REAL** (AI) | Words are AI; numbers never are |
| Bank + Account Aggregator data | **PRE-SEEDED** synthetic, disclosed in-app | Live bank/AA APIs arrive in the sandbox stage |
| Omni-channel delivery (voice/SMS/WhatsApp/push) | **SIMULATED** playback of *real* AI copy | Telephony/messaging infra is out of prototype scope |
| Vanilla auto-execute | **SIMULATED** confirmation + receipt | No real money movement |

## How it works

```
                         ┌─────────────────────────┐
                         │   Customer mobile app    │
                         │  chat · dashboard · RM   │
                         │  desk · omni-channel     │
                         └───────────┬──────────────┘
                                     │
                         ┌───────────▼──────────────┐
                         │        AI companion       │
                         │      (tool-use agent)     │
                         └───────────┬──────────────┘
                                     │ every number via a tool call
                         ┌───────────▼──────────────┐
                         │   Deterministic spine     │
                         │  analytics → suitability  │
                         │  matrix → routing engine  │
                         └───────────┬──────────────┘
                                     │
                         ┌───────────▼──────────────┐
                         │  Customer + product data  │
                         └───────────────────────────┘
```

**"Compute the numbers, generate the words."** Every figure or classification a bank
must defend — spend categories, cash-flow, net-worth, two-axis risk, suitability
segment, product eligibility, and the auto-execute / RM-lead / suppress decision — is
computed deterministically and never touched by the AI. The AI only explains, phrases,
and selects *within* what the deterministic layer already decided. The AI provider
itself is a swappable component, so the bank is never locked to one vendor.

## Compliance by construction

- **Regulated products never auto-execute.** A deterministic engine — not the AI —
  decides vanilla (instant) vs. regulated (RM Lead Packet). Enforced in code, tested in
  all three languages.
- **Every figure is traceable.** The AI never emits a number it didn't get from a
  calculation; an in-app Audit view shows the trail behind every reply.
- **Distress suppresses selling.** Past an EMI-burden threshold, all product nudges are
  suppressed in favour of debt-help and literacy.
- **Dual, explicit consent.** An Account Aggregator artefact authorises data *transfer*;
  a separate DPDP consent authorises *processing / advisory use*. Both explicit, both
  revocable, neither substitutes for the other.
- **Synthetic data only — never real PII.** Every persona, transaction, and holding is
  generated and disclosed as such.

## Links

- **Live demo:** https://wealthmitra.onrender.com/

## Team

Built for **IDBI Innovate 2026** by **Team 404 Sleep Not Found**.
