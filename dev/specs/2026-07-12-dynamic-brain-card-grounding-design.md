# Design — Dynamic, human-like advisory brain + real-IDBI card grounding

**Date:** 2026-07-12
**Status:** Approved (design); spec under user review
**Scope:** WealthMitra demo (`wealthmitra/`) — backend brain + card catalogue + frontend loader; deploy provider swap.

---

## 0. Problem

Two observed failures and one design gap, surfaced by the "Which CC should I get?" chat for the NRI persona Arjun Nair (Dubai, 35):

- **Bug A — classification gap.** "CC" (and any card phrasing without the literal word `card`) is not recognized as a card query. It falls through to generic *info* mode, where the LLM is handed only the **investment** catalogue (which contains no credit cards) and **improvises** a card answer. This is an ungrounded reply — the exact "compute the numbers, generate the words" violation the architecture exists to prevent.
- **Bug B — cold, dead-end ineligibility.** Genuinely-ineligible customers get a terse refusal: no honest reason, no realistic alternative, no RM handoff, no empathy.
- **Gap — the brain is scripted, not dynamic.** Card discovery and onboarding are hand-written regex state machines. The system does not decide *what to ask and when to act* based on conversation + profile; it feels like a decision tree.

Two facts confirmed during investigation:
- **There is no RAG anywhere in the code.** The recommendation engine is 100% deterministic rules (a suitability matrix for investments + a static card product-master). "Hybrid RAG" is a documented *future* plan, not shipped. The deck must not claim RAG is live.
- **The card master is small and partly fictional.** It models 3 cards; real IDBI has 7. Eligibility must be grounded in real IDBI data.

## 1. Goals / non-goals

**Goals**
1. Fix the classification gap so card queries always reach the deterministic card-eligibility engine (never LLM improvisation).
2. Ground card eligibility in **real IDBI card data**, calibrated so **some personas are eligible and some are not — all for honest, source-backed reasons**.
3. Make the brain **smart-deterministic**: deterministic compliance spine (routing, eligibility, every number, lead creation) with a **dynamic conversation** on top — the LLM decides, each turn, whether to ask a clarifying question, call a tool, answer, offer an RM handoff, or offer AA-connect.
4. **Empathy on ineligible:** acknowledge honestly → surface a realistic alternative if one exists → offer RM handoff, lead created only on consent and tagged *exploratory*.
5. **AA-connect reachable in chat** so the Account Aggregator + dual-consent story is visible to a judge who never opens the dashboard.
6. **Intent-aware "thinking" loader** so waiting reads as reasoning.
7. **Swap the deploy LLM** to a faster, still-free-or-cheap provider with a cheap/smart model split.

**Non-goals (cut for this demo round)**
- Real RAG / vector retrieval (stays deterministic; deck says "RAG = roadmap").
- LIC co-brand cards (Lumine, Eclat) — require being an LIC policyholder; out of scope.
- Real FCNR-FD-opening execution — the RM handles it; we only route the lead.
- Rebuilding the scripted "New to IDBI" 4-question onboarding — kept as-is.

## 2. Real IDBI card data (grounding + eligibility spread)

Real, source-backed IDBI lineup (as of 2026-07-12; sources: IDBI official pages + Imperium FAQ PDF, Paisabazaar, Bankbazaar). The unlock: **Imperium Platinum is a secured-against-FD card whose FAQ explicitly accepts FCNR deposits — the standard NRI on-ramp.**

| Card | Tier | Real rule (source-backed) | Demo role |
|---|---|---|---|
| **Aspire Platinum** | Entry, lifetime-free | 21–60 (65 self-emp), **India resident**, no published income (discretionary) | Broadly eligible → resident adults |
| **Royale Signature** | Upper-mid, lifetime-free | 21–60/65, India resident (income unofficial — do NOT hardcode a threshold) | Eligible → resident, mid income |
| **Euphoria World** | Premium travel | 21–60/65, India resident, ₹1,499 fee (waived ₹1.5L spend) | Eligible → resident, higher income |
| **Winnings** | RuPay rewards | 21–60, **Indian citizen + resident** | Eligible → resident citizen |
| **Imperium Platinum** | **Secured vs FD/FCNR** | **18+, no income proof, min ₹20k FD (FCNR ok)** | **The NRI / thin-file on-ramp** |

**Data changes**
- Replace `backend/config/credit_offers.json` card entries with the 5 real cards above and their real published rules. Where IDBI does not publish an income figure, model it as *discretionary* (no hard income gate) rather than inventing a threshold.
- Add residency semantics: unsecured cards require `resident_india: true`; Imperium requires an **IDBI FD or FCNR deposit ≥ ₹20,000** (`requires_idbi_fd_min: 20000`, `accepts_fcnr: true`).
- **Persona seed calibration** (`data/synthetic/*.json`): read each of the 7 seeds and align income / residency / IDBI-FD fields to the real rules so verdicts are honest and produce a spread:
  - **Arjun Nair** (NRI, Dubai): unsecured → **ineligible** (resident-only); Imperium → **eligible path once an NRE/FCNR FD is visible** (drives the empathy + AA loop, §4/§5).
  - At least **2 personas clearly eligible** for unsecured cards (resident salaried/business — e.g. Ravi, Devika).
  - At least **1 needs-more-data or entry-only** (thin-file / senior).
  - **Vikram** (distress): selling **suppressed entirely** — unchanged.
- Exact per-persona verdicts finalized when the seeds are read during implementation; the target spread above is the contract.

## 3. The brain — smart-deterministic, dynamic conversation

**Per-turn loop:**

```
[DETERMINISTIC gate]  intent classify → route (mode)      ← compliance spine, position unchanged
      ↳ classifier upgraded: keyword-first, then a cheap LLM fallback
        ONLY for the "other" bucket (catches "CC", typos, hi/gu variants)
[DYNAMIC in-mode]     LLM given: profile + KNOWN facts + a "required-context
                      checklist" (gaps for this intent) + the mode's tool set,
                      decides each turn one of:
                        ask a clarifying question / call a tool / answer /
                        offer RM handoff / offer AA-connect
[DETERMINISTIC]       eligibility, every number, lead-packet = tool-computed
[GUARDRAIL]           number-audit on output (unchanged)
```

**Key properties**
- The **compliance gate stays deterministic and runs first** — routing/mode is fixed before any generative decision. This keeps the cockpit audit trail true.
- **Dialogue is dynamic**: within the routed mode, the LLM decides what to ask and when to act, driven by a per-intent **required-context checklist** (the profile gaps that matter for this intent). This replaces the rigid card state machine.
- **Numbers and eligibility are never generated** — they come from deterministic tools; the guardrail audits the output for any un-sourced figure.

**Concrete changes**
1. **Classifier robustness** (`backend/app/routing/intents.py`, `backend/app/agent/orchestrator.py`): add `cc` and common synonyms to card aliases; broaden the generic-card regex. Add a **cheap LLM fallback classifier** invoked *only* when keyword classification returns `other`, mapping to the same fixed intent set (so routing stays deterministic on the classifier's output). Multilingual (en/hi/gu).
2. **Reachable card engine**: add a `credit_card` product category and expose the deterministic card-eligibility engine as a **tool** the brain can call — `evaluate_card_eligibility(profile) -> per-card {status, reason, alternative}`. In `loans_cards` mode the brain gets this tool (not the investment shelf).
3. **Retire the scripted card state machine** (`orchestrator.py` `pending_credit` 3-stage regex flow); the card conversation now runs through the dynamic in-mode loop with the checklist (need? residency? IDBI-FD?) + the eligibility tool.
4. **Lead creation stays deterministic**: a lead is created only via a tool call the LLM invokes on consent; the engine enforces tagging (eligible vs. `exploratory / not-yet-eligible`) and never implies approval.
5. **AA-connect action** — `offer_aa_connect` (see §5) added to the brain's action set.

## 4. Empathy / ineligible → RM

When the eligibility tool returns no eligible unsecured card but a secured alternative exists (Imperium / FCNR):
1. **Acknowledge honestly** — name the real reason ("those cards are set up for India-resident profiles, so they wouldn't fit your NRI status — I don't want to set a wrong expectation").
2. **Surface the realistic alternative** — Imperium secured against an NRE/FCNR FD.
3. **Offer RM on consent** — on "yes", create the RM lead, tagged **`exploratory / not-yet-eligible`** so the RM has honest context. Never implies approval. If "no", no lead; offer general guidance/literacy instead.

## 5. AA-connect in chat + demo loop

**`offer_aa_connect`** — a proactive brain action so the Account Aggregator + dual-consent story is visible in chat (not only on the dashboard).

- **Fires when:** the profile shows unconnected external data, OR the user asks something needing a fuller picture ("what's my net worth?", "which card should I get?").
- **Behavior:** the brain *offers* ("to give you the full picture — MFs, other-bank deposits, insurance — I'd need to link them via Account Aggregator; want to connect them?"). On **"yes"** → triggers the **existing dual-consent flow** (AA data-transfer consent ≠ DPDP processing consent — both explicit, revocable), then newly-visible holdings recompute net-worth **live in chat** (tool-sourced, audited). Never auto-pulls.
- **Calibration:** set **at least Arjun (ideally 1–2 more) to "AA-not-yet-connected"** so the offer genuinely appears.

**The Arjun demo loop (chat-only, showcases everything):**
asks about a card → decline unsecured (honest reason) → *"if we connect your accounts via AA, I can see your NRE/FCNR deposits — that's exactly what qualifies you for the Imperium secured card"* → AA dual-consent → external FD becomes visible → Imperium eligibility flips to a real path → RM handoff (exploratory). One natural thread demonstrates AA + dual-consent + cards + eligibility + RM.

## 6. Loader / "thinking" states

Replace the flat spinner with a **staged, intent-aware status** driven by the brain's current phase:
`"Understanding your question…" → "Checking your profile…" → "Looking at IDBI cards…" / "Reviewing your holdings…" → "Almost ready…"`
The status is derived from which phase the pipeline is in (classify → tool-calls → drafting), so it reflects real work, and doubles as a subtle "the deterministic engine is working" signal for judges. Frontend-only; low effort.

## 7. LLM deploy provider

Criteria: usable free tier (or cheap credits), fast (low TTFT + high tok/s — the current Gemini pain), reliable tool/function-calling (our brain's spine), Hindi/Gujarati competence, and a cheap-small + smart-large model split from **one** provider so we route by `task_class`. Our gateway is already provider-agnostic (`anthropic` / `gemini` / `claude_cli`); every fast-inference alternative exposes an **OpenAI-compatible endpoint**, so we add **one generic `openai_compatible` adapter** (base_url + key) and unlock Groq / OpenAI / Cerebras / Mistral with a config swap.

### 7.1 Decision

**Root-cause note:** the "slow/old" pain is partly that we're pinned to an old Gemini model ID, and partly that Gemini's **free tier is deprioritized under load** — so even a current model can stall during live judging. Fix the model ID, but don't rely on free-tier Gemini as the sole live path.

**Primary deploy = OpenAI `gpt-5.4-mini` / `gpt-5.4-nano`** (via the new `openai_compatible` adapter). Chosen because **tool-calling is the compliance spine** and OpenAI's `strict:true` gives schema-guaranteed tool calls — eliminating the "model skips a tool → improvises an ungrounded answer" failure mode (the exact class of bug being fixed). Demo cost is negligible.
- `simple` turns (greeting, literacy, short narration) → **`gpt-5.4-nano`** ($0.20 in / $1.25 out; cached in $0.02).
- `complex` turns (tool loop, reasoning) → **`gpt-5.4-mini`** ($0.75 in / $4.50 out; cached in $0.075).
- **Cost:** ~5¢ per ~10-turn conversation; whole judging period well under $5. No free tier (pay from token 1), but the amount is a rounding error.
- **Speed:** small tiers, ~150–215 tok/s **streaming** → short replies in 1–3s, a large jump over old-Gemini-on-free-tier. Not Groq-fast, but good enough and reliable.
- Use `strict:true` on every tool definition; keep the number-audit guardrail regardless.

**Immediate free fix (zero code, do first):** bump the existing `gemini` adapter's model ID to **`gemini-2.5-flash-lite`** — kills most of the "slow/old" complaint on the adapter we already have. Keep Gemini `2.5-flash-lite` as the configured **free fallback** provider.

**Alternative — max speed at zero cost:** Groq via the same adapter (`gpt-oss-20b` simple / `gpt-oss-120b` complex) — free, ~1000 tok/s, but requires `tool_choice:"required"` + a JSON-validate-and-retry wrapper because Groq can skip tools. Documented as the fallback if OpenAI credits aren't available; not primary because the tool-skip risk works against the compliance spine.

**Multilingual caveat (verification item):** Gujarati is the weak spot — Gemini's GU is weak, Groq's `gpt-oss` GU is undocumented, only Mistral documents GU. Verify Gujarati quality on the chosen model against the **Meera Patel** persona; if weak, route `gu` turns to Gemini 2.5-flash or Mistral `mistral-small-latest`. Do not claim GU quality on the deck without this check.

**Config-only, reversible:** provider + per-`task_class` model IDs live in gateway config; switching Groq↔OpenAI↔Gemini is a config change, no downstream code change (the whole point of the provider-agnostic gateway — a live deck proof point).

## 8. Scope summary

**Build**
- Real IDBI card master (5 cards) + persona seed calibration for an eligible/ineligible spread.
- Classifier robustness (`cc` + synonyms + LLM fallback on `other`).
- `credit_card` category + `evaluate_card_eligibility` tool; retire scripted card state machine.
- Dynamic in-mode loop (checklist + LLM decides ask/tool/answer/RM/AA) — proven on the card flow.
- Empathy → secured → RM (consent, exploratory tag).
- `offer_aa_connect` in chat wired to existing dual-consent + live-recompute.
- Intent-aware "thinking" loader.
- Deploy provider swap (adapter + model routing, per §7).

**Cut**
- RAG, LIC cards, real FCNR-FD execution, onboarding rebuild.

## 9. Verification

- Unit: classifier maps "CC"/"which card"/hi-gu variants → card intent; card-eligibility engine returns correct status per persona; ineligible/needs-more-data never create a non-exploratory lead.
- Flow (browser): (1) Ravi/Devika → card query → eligible shortlist. (2) Arjun → card query → decline unsecured → Imperium+AA offer → AA consent → Imperium path → RM exploratory lead. (3) Vikram → selling suppressed. (4) net-worth query with unconnected data → AA offer in chat → live recompute. (5) loader shows staged states.
- No un-sourced number passes the guardrail; audit trail shows the deterministic path for every card verdict.
