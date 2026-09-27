# Vera — MagicPin AI Merchant Assistant Challenge

![Status](https://img.shields.io/badge/status-production%2Bready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)

A production-ready AI chatbot that engages Indian merchants on WhatsApp, helping them grow their Google Business Profiles and run marketing campaigns.

## Quick Start

### Prerequisites
- Python 3.11+
- pip or poetry
- Docker (optional)

### Local Development

**1. Clone & Setup**
```bash
cd vera-challenge
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure**
```bash
cp .env.example .env
# Edit .env with your team info
```

**3. Run Locally**
```bash
python app.py
```

The server will start at `http://localhost:8080`

**4. Test Health**
```bash
curl http://localhost:8080/v1/healthz
```

Expected response:
```json
{
  "status": "ok",
  "uptime_seconds": 42,
  "contexts_loaded": {
    "category": 0,
    "merchant": 0,
    "customer": 0,
    "trigger": 0
  }
}
```

### Run with Docker

**1. Build**
```bash
docker build -t vera-bot .
```

**2. Run**
```bash
docker run -p 8080:8080 \
  -e TEAM_NAME="Your Team" \
  -e CONTACT_EMAIL="your@email.com" \
  vera-bot
```

---

## Architecture

### API Endpoints

**POST /v1/context**
- Receive category, merchant, customer, and trigger context from judge
- Implements versioning (reject stale versions, accept newer)
- Response: acknowledgment with stored_at timestamp

**POST /v1/tick**
- Periodic wake-up (every 5 simulated minutes)
- Judge provides list of available triggers
- Bot decides which to act on and composes proactive messages
- Returns list of actions to send

**POST /v1/reply**
- Handle merchant/customer replies
- Parse intent (yes/no/wait/unclear)
- Detect auto-replies
- Return next action: send/wait/end
- 30-second timeout

**GET /v1/healthz**
- Liveness probe (judge polls every 60s)
- 3 consecutive failures = disqualification

**GET /v1/metadata**
- Bot identity and submission info
- Model, approach, team, contact

### Core Modules

```
engine/
├── context_store.py      # Versioned context storage
├── conversation.py       # Multi-turn conversation state
├── trigger_ranker.py     # Trigger scoring and selection
├── composer.py           # Message composition (deterministic)
├── intent.py             # Intent recognition (yes/no/wait)
└── consent.py            # Customer consent checking
```

### Decision Flow

```
Tick → Rank Triggers → Select Top → Load Contexts → Compose → Validate → Return Actions
                                              ↓
Reply → Recognize Intent → Check Auto-Reply → Decide Action (send/wait/end)
```

---

## Scoring Rubric

Each action is scored on 5 dimensions (0-20 each):

### 1. Decision Quality
- Right trigger at right time
- Respect conversation state
- Detect auto-replies and escalations
- Recognize merchant intent

### 2. Specificity
- Use real numbers (CTR, calls, views)
- Cite sources correctly (JIDA Oct 2026 p.14)
- Real merchant names, localities
- No hallucinated data

### 3. Category Fit
- Correct tone (peer/clinical for dentists, motivation for gyms, etc.)
- Approved vocabulary
- Avoid taboos (e.g., "guarantee", "cure" for dentists)
- Service+price over generic discounts

### 4. Merchant Fit
- Personalized (name, location, performance, cohort, signals)
- Reference active offers
- Address merchant problems
- Use customer aggregate data

### 5. Engagement Compulsion
- Use 1-2+ compulsion levers naturally
- Specificity, loss aversion, social proof, effort externalization, curiosity, reciprocity
- Single binary CTA (YES/STOP)
- Clear call to action

---

## Key Features

### ✅ Context Versioning
- Accept first version
- Reject stale versions (409 with current_version)
- Replace atomically with newer versions
- Never lose context

### ✅ Conversation State Machine
- States: initiated → awaiting_reply → intent_action / waiting / ended / escalated
- Multi-turn tracking
- Suppression key tracking
- Auto-reply detection

### ✅ Trigger Ranking
- Score by urgency, type, performance, freshness
- Select top priority trigger
- Route to appropriate composer

### ✅ Message Composition
- Deterministic (no LLM dependency)
- Template-based routing per trigger type
- Variable substitution from context
- Output validation

### ✅ Intent Recognition
- Affirm: yes, sure, go ahead, kar do, haan
- Negate: no, not interested, stop, remove me
- Wait: later, tomorrow, call me after
- Unclear: fallback (ask clarification)

### ✅ Consent Enforcement
- Require explicit consent for customer outreach
- Check scope: [recall_reminders, appointment_reminders, ...]
- Hard gate (no exceptions)

### ✅ Anti-Patterns Prevented
- No generic offers ("Flat 30% off" → "Haircut @ ₹99")
- No multiple CTAs ("YES for X, NO for Y, MAYBE for Z" → single action)
- No hallucinated data
- No repeated messages in same conversation
- No customer contact without consent

---

## Testing Locally

### Run Judge Simulator
```bash
# In another terminal, ensure app.py is running on localhost:8080
export BOT_URL=http://localhost:8080
python judge_simulator.py
```

This runs the LLM-powered judge and scores your bot on:
- Decision quality
- Message specificity
- Category fit
- Merchant fit
- Engagement compulsion

### Run Unit Tests
```bash
pytest tests/
```

Tests cover:
- Context versioning
- Trigger ranking
- Intent recognition
- Consent checking
- API contract
- Message composition

---

## Dataset

The challenge provides:

**Categories** (5):
- dentists.json
- salons.json
- restaurants.json
- gyms.json
- pharmacies.json

Each contains:
- offer_catalog
- voice (tone, vocabulary, taboos)
- peer_stats (benchmarks)
- digest (research, compliance, trends)
- seasonal_beats
- trend_signals

**Seed Data**:
- merchants_seed.json (10 merchants × 5 categories)
- customers_seed.json (15 customers)
- triggers_seed.json (25 trigger templates)

**Generator**:
- generate_dataset.py (expands seed to full test dataset)

---

## Configuration

### Environment Variables

```bash
TEAM_NAME=Your Team Name
TEAM_MEMBERS=Alice,Bob,Charlie
CONTACT_EMAIL=team@example.com
BOT_VERSION=1.0.0
PORT=8080
HOST=0.0.0.0
LOG_LEVEL=INFO
```

### Optional LLM (for future enhancement)

If you want to add LLM-based message polishing:

```bash
LLM_PROVIDER=anthropic  # or openai, google, etc.
LLM_MODEL=claude-opus-4-7-20250219
LLM_API_KEY=your-api-key
```

Then modify `engine/composer.py` to use LLM for polishing.

---

## Deployment

### Deploy to Render (Recommended)

1. Push code to GitHub
2. Connect GitHub repo to Render
3. Upload `render.yaml`
4. Set environment variables in Render dashboard
5. Deploy

Public URL: `https://vera-bot-<team-name>.onrender.com`

### Deploy to Heroku

```bash
heroku create vera-bot-<team-name>
git push heroku main
heroku config:set TEAM_NAME="Your Team"
```

### Deploy to AWS, GCP, etc.

Use the provided `Dockerfile`:

```bash
docker build -t vera-bot .
# Push to ECR / Artifact Registry
# Deploy via ECS / Cloud Run / similar
```

---

## Documentation

- `docs/challenge-understanding.md` — Complete challenge spec and implementation guide
- `docs/architecture.md` — Detailed architecture and design decisions
- `docs/decision-engine.md` — Trigger ranking and decision logic
- `docs/testing.md` — Testing strategy and results

---

## Project Structure

```
vera-challenge/
├── app.py                          # FastAPI entry point
├── engine/
│   ├── context_store.py            # Versioned context storage
│   ├── conversation.py             # Conversation state machine
│   ├── trigger_ranker.py           # Trigger scoring
│   ├── composer.py                 # Message composition
│   ├── intent.py                   # Intent recognition
│   └── consent.py                  # Consent checking
├── models/
│   └── context.py                  # Pydantic schemas
├── tests/
│   ├── test_context_store.py
│   ├── test_intent.py
│   ├── test_consent.py
│   └── test_api_contract.py
├── scripts/
│   └── run_judge_simulator.sh
├── docs/
│   ├── challenge-understanding.md
│   ├── architecture.md
│   └── testing.md
├── dataset/                        # Judge-provided datasets
│   ├── categories/
│   ├── merchants_seed.json
│   ├── customers_seed.json
│   └── triggers_seed.json
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

---

## Performance Requirements

- **Tick timeout**: 30 seconds
- **Reply timeout**: 30 seconds
- **Healthz timeout**: 5 seconds
- **Target latency**: < 1 second for deterministic paths

The bot is lightweight and deterministic (no slow external APIs except optional LLM).

---

## Submission Checklist

Before submitting to the judge:

- [ ] All 5 endpoints implemented and tested
- [ ] Context versioning works (idempotent, stale rejection)
- [ ] Conversation state persisted correctly
- [ ] Trigger ranking is deterministic
- [ ] Messages use only provided data (no hallucinations)
- [ ] Auto-reply detection works
- [ ] Intent recognition (yes/no/wait) accurate
- [ ] Consent checking for customer outreach
- [ ] Suppression prevents repetition
- [ ] Category-specific behavior for all 5 categories
- [ ] Merchant personalization across all fields
- [ ] No hardcoded test cases
- [ ] All tests passing
- [ ] Judge simulator running
- [ ] Docker builds successfully
- [ ] Public endpoint reachable and responding
- [ ] .env.example provided (no secrets in repo)
- [ ] Git pushed with clean history
- [ ] README complete with setup instructions
- [ ] URL submitted via challenge portal

---

## Troubleshooting

**Q: API returns 409 on context push**
A: You're trying to push an older version of context. The judge already has a higher version. This is correct behavior (stale_version rejection).

**Q: Healthz fails but my code looks good**
A: Ensure `/v1/healthz` returns 200 within 30 seconds. Check context loading logic.

**Q: Tick timeouts**
A: Tick is taking > 30 seconds. Optimize trigger ranking, context loading, or message composition.

**Q: Merchant says "yes" but I ask another question**
A: Intent detection issue. Call `recognize_intent()` and check if "affirm" is being caught. See `engine/intent.py` patterns.

**Q: Messages are too generic**
A: Use real data from contexts. Check that merchant name, performance metrics, and offers are being populated from context payload, not hallucinated.

---

## Evaluation Timeline

1. **Local testing**: Judge simulator (2-3 days)
2. **Baseline testing**: Judge harness with base dataset (1 day)
3. **Robustness testing**: New merchants, customers, triggers (1 day)
4. **Conversation depth**: Multi-turn, intent transitions (1 day)
5. **Replay**: Dynamic context injection mid-test (1 day)
6. **Final scoring**: 5-dimension rubric on all actions

---

## Support & Questions

- Review `challenge-brief.md` for the official spec
- Review `challenge-testing-brief.md` for API contract
- Check `docs/` folder for detailed design docs
- Review case studies in `examples/`
- Run judge_simulator.py locally to debug

---

## License & Ethics

- All data is synthetic (no real PII)
- Submission for challenge evaluation only
- Do not scrape real magicpin/Google data
- Respect merchant and customer privacy
- All contexts provided by judge are fair game

---

## Changelog

**v1.0.0** (2026-04-26)
- Initial submission
- All 5 endpoints implemented
- Context versioning with stale rejection
- Trigger ranking and composition
- Intent recognition and auto-reply detection
- Consent enforcement
- Multi-turn conversation state
- Category-aware messaging
- Merchant personalization

---

**Build something better than today's Vera.** 🚀

Good luck!
