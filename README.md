# WealthMitra (धन मित्र)

**IDBI Innovate 2026 · Track 01 · Wealth Advisory / Conversational AI / Mobile Banking**
Team **404 Sleep Not Found**

Wealth advisory in India is human-gated: an RM calls you if your balance is big enough. Everyone else gets generic banners. WealthMitra is a vernacular, AI wealth **companion** embedded in the bank's mobile app — it reads a customer's real transaction behaviour and out-of-bank holdings and turns them into personalized, data-grounded guidance. Simple products execute instantly; regulated products convert into structured, high-context leads for a human Relationship Manager.

**We are a companion, not an adviser.** SEBI reserves "Adviser/Wealth Manager" for Registered Investment Advisers. WealthMitra does information and distribution — factual, data-grounded, in the customer's own language. The word "advice" for a personalised, suitability-driven recommendation on a regulated product belongs to the human RM path, always. That line isn't a branding choice, it's load-bearing: it's what lets an AI companion operate at bank scale without stepping into regulated advisory territory.

## What the demo shows

1. **Grounded AI chat, in English / हिंदी / ગુજરાતી.** Ask it anything about your money — every number in the reply traces to a real tool call over the persona's synthetic data, never a hallucinated figure. Switch language mid-conversation.
2. **Vanilla product, auto-executed.** Ask about a plain-vanilla SIP or FD and watch it execute live, with a receipt — no human in the loop, because nothing here is regulated advice.
3. **Regulated ask → a live Lead Packet on the RM desk.** Ask about equity, ULIPs, or anything suitability-driven, and the deterministic routing engine (not the LLM) converts it into a structured Lead Packet that appears on the RM dashboard in real time — the money-shot that proves the compliance boundary is enforced in code, not by prompt.
4. **Distress → selling suppressed.** For a persona whose EMIs eat a large share of income, the engine suppresses all product nudges and routes to debt-help + literacy only. The companion is on the customer's side first.

## Real vs pre-seeded vs simulated — the honest line

Every feature in this demo is one of these three. We say so up front in the app itself; here it is again for anyone reading the code.

| Layer | Status | Note |
|---|---|---|
| Chat answers (LLM tool-use agent, any provider) | **REAL** — live LLM calls, grounded in tools | Type anything, get a real grounded reply |
| All figures (spend, cash-flow, net-worth, two-axis risk, suitability segment) | **REAL, deterministic** | The "compute the numbers" compliance spine |
| Routing (vanilla-auto vs RM-lead vs distress-suppress) | **REAL, deterministic** | 100% test-covered, the compliance money-shot |
| Suitability Matrix product filtering | **REAL, deterministic (config-driven)** | Governance/scalability story |
| 3-surface live sync (chat → RM queue → nudge) | **REAL** (realtime channel) | The "wow" |
| Nudge copy, RM lead narrative, multilingual replies | **REAL** (LLM) | Words are AI; numbers are not |
| Data ingestion (bank + Account Aggregator) | **PRE-SEEDED** synthetic, disclosed in-app | Can't wire live bank/AA APIs pre-sandbox |
| Omni-channel *delivery* (voice/SMS/WhatsApp/push) | **SIMULATED** playback of *real* AI copy | Telephony/messaging infra is out of scope for a prototype |
| Vanilla auto-execute | **SIMULATED** confirmation + receipt | No real money movement |

## Architecture

```
                         ┌─────────────────────────┐
                         │   React SPA (frontend)   │
                         │  chat · dashboard · RM   │
                         │  desk · omni-channel      │
                         └───────────┬──────────────┘
                                     │ /api (REST) + /ws (realtime)
                         ┌───────────▼──────────────┐
                         │      FastAPI backend      │
                         │                            │
   ┌─────────────────┐  │  ┌──────────────────────┐  │
   │  Model Gateway   │◄─┼──┤   Agent Orchestrator │  │
   │ claude_cli /     │  │  │  (tool-use loop)     │  │
   │ gemini / anthropic│  │  └──────────┬───────────┘  │
   └─────────────────┘  │             │ tool calls     │
                         │  ┌──────────▼───────────┐   │
                         │  │   Deterministic spine  │  │
                         │  │  analytics → suitability│ │
                         │  │  matrix → routing engine│ │
                         │  └──────────┬───────────┘   │
                         │             │                │
                         │  ┌──────────▼───────────┐    │
                         │  │  Synthetic persona &   │   │
                         │  │  product-catalogue data│   │
                         │  └────────────────────────┘   │
                         └────────────────────────────────┘
```

**"Compute the numbers, generate the words."** Every figure or classification a bank has to defend — spend categories, cash-flow, net-worth, two-axis risk, suitability segment, product eligibility, and the auto-execute/RM-lead/suppress routing decision — is deterministic Python, unit-tested, and never touched by the LLM. The LLM only explains, phrases, and selects within whatever the deterministic layer already decided. The Model Gateway is the one deliberate abstraction: swap `LLM_PROVIDER` and every other service is unaffected.

## Quickstart (local)

Requires Python 3.12 and Node 20.

```bash
conda create -n wealthmitra python=3.12 -y   # or any venv of your choice
conda activate wealthmitra

make install   # pip install -r backend/requirements.txt
make build     # compiles backend, npm ci + npm run build for the frontend
make run       # PYTHONPATH=backend uvicorn app.main:app --port 8000
```

Open http://localhost:8000. By default `LLM_PROVIDER=claude_cli`, which shells out to the `claude` CLI — only works if that's installed and authenticated on your machine. To run against Gemini or Anthropic instead:

```bash
cp .env.example .env
# edit .env: LLM_PROVIDER=gemini, GEMINI_API_KEY=<your key>
make run
```

A missing key for whichever provider is active fails app startup immediately, with a clear error — by design, so a misconfigured deploy fails loudly instead of silently degrading.

## One-click deploy (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Click the button (or go to the [Render Dashboard](https://dashboard.render.com/blueprints) → **New Blueprint Instance**) and point it at this repo.
2. Render reads `render.yaml`, builds the Docker image, and prompts you for **`GEMINI_API_KEY`** during setup (the only value it can't infer).
3. Wait for the build — first deploy takes a few minutes (Node + Python multi-stage build). Health check is `/api/health`.

The deployed default is **`LLM_PROVIDER=gemini`** — `claude_cli` is a dev-machine-only provider and is never valid in a container. See `render.yaml` and `.env.example` for the full contract.

### Manual Docker

```bash
docker build -t wealthmitra .
docker run -p 8000:8000 -e LLM_PROVIDER=gemini -e GEMINI_API_KEY=<your key> wealthmitra
```

## Testing

```bash
make test   # backend/tests — 500+ tests: analytics math, suitability matrix
            # coverage, routing compliance (regulated never auto-executes, in
            # all 3 languages), i18n rendering, lead dedup, execute validation,
            # nudge policy, and number-traceability
```

## Compliance by construction

- **Regulated products never auto-execute.** A deterministic routing engine — not the LLM — decides vanilla (instant execution) vs. regulated (RM Lead Packet); this is enforced in code and covered by tests across all three languages.
- **Every figure is tool-sourced, with an audit trail.** The LLM never emits a number it didn't get from a tool call; the in-app Audit view shows the tool-call trail behind every reply.
- **Distress suppresses selling.** When EMI burden crosses a threshold, the engine suppresses all product nudges and routes to debt-help + literacy only.
- **Dual, explicit consent.** An Account Aggregator artefact authorises data *transfer*; a separate DPDP consent authorises *processing/advisory use*. Both are explicit and revocable, and neither substitutes for the other.
- **Synthetic data only — never real PII.** Every persona, transaction, and holding in this repo is generated, seeded, and disclosed as such.

## Repo map

```
backend/    FastAPI app — agent orchestrator, model gateway, analytics,
            suitability catalogue, routing engine, nudges, tests
frontend/   Vite + React + TypeScript SPA — customer chat/dashboard,
            RM desk, omni-channel showcase, presenter split-view
data/       Synthetic persona + transaction generator and generated seed data
```

## License / team

Built for the **IDBI Innovate 2026** proposal round by **Team 404 Sleep Not Found**.
