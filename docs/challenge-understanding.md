# MagicPin Vera AI Challenge — Complete Understanding

**Compiled from**: challenge-brief.md, challenge-testing-brief.md, engagement-design.md, dataset, judge_simulator.py  
**Status**: Master reference for building production-ready submission  
**Last Updated**: 2026-04-29

---

## 1. CHALLENGE OBJECTIVE

Build an AI merchant-growth assistant ("Vera") that:
- Engages merchants over WhatsApp intelligently
- Helps them improve Google Business Profile, run campaigns, manage offers
- Handles both merchant→Vera and customer→Vera interactions
- Makes thoughtful decisions about WHEN, WHAT, WHO, and HOW to message

**Success Criteria**: Score high on **5 dimensions** (§8):
1. Decision Quality
2. Specificity
3. Category Fit
4. Merchant Fit
5. Engagement Compulsion

---

## 2. THE 4-CONTEXT FRAMEWORK

Every Vera message is composed from structured input across 4 dimensions:

### 2.1 CategoryContext (slow-changing, ~5 total)
```
{
  slug: "dentists" | "salons" | "restaurants" | "gyms" | "pharmacies"
  offer_catalog: [OfferTemplate, ...]  # "Service @ ₹Price"
  voice: {tone, vocab_allowed, vocab_taboo, salutation_examples, tone_examples}
  peer_stats: {avg_rating, avg_reviews, avg_ctr, avg_views, avg_calls, ...}
  digest: [DigestItem, ...]  # research/compliance/trend/CDE items
  patient_content_library: [ContentItem, ...]  # shareable content
  seasonal_beats: [{month_range, note}, ...]  # e.g., "exam-stress bruxism Nov-Feb"
  trend_signals: [{query, delta_yoy, segment_age}, ...]
}
```

### 2.2 MerchantContext (per-merchant, ~50 total in tests)
```
{
  merchant_id: "m_001_drmeera_dentist_delhi"
  category_slug: "dentists"
  identity: {name, city, locality, place_id, verified, languages, owner_first_name}
  subscription: {status, plan, days_remaining}
  performance: {window_days, views, calls, directions, ctr, leads, delta_7d}
  offers: [{id, title, status, started/ended}, ...]
  conversation_history: [{ts, from, body, engagement}, ...]
  customer_aggregate: {total_unique_ytd, lapsed_180d_plus, retention_6mo_pct, ...}
  signals: ["stale_posts:22d", "ctr_below_peer_median", "engaged_in_last_48h", ...]
  review_themes: [{theme, sentiment, occurrences_30d, common_quote}, ...]
}
```

### 2.3 TriggerContext (events, ~100 in full tests)
```
{
  id: "trg_001_research_digest_dentists"
  scope: "merchant" | "customer"
  kind: "research_digest" | "perf_spike" | "perf_dip" | "recall_due" | ...
  source: "external" | "internal"
  merchant_id: "m_001_drmeera_dentist_delhi"
  customer_id: null | "c_001_priya_for_m001"
  payload: {category, top_item_id, ...}  # trigger-specific data
  urgency: 1-5
  suppression_key: "research:dentists:2026-W17"
  expires_at: datetime
}
```

### 2.4 CustomerContext (relationship data, optional, ~200 in full tests)
```
{
  customer_id: "c_001_priya_for_m001"
  merchant_id: "m_001_drmeera_dentist_delhi"
  identity: {name, phone_redacted, language_pref, age_band}
  relationship: {first_visit, last_visit, visits_total, services_received, lifetime_value}
  state: "lapsed_soft" | "active" | "lapsed_hard" | ...
  preferences: {preferred_slots, channel, reminder_opt_in}
  consent: {opted_in_at, scope: [recall_reminders, appointment_reminders, ...]}
}
```

---

## 3. API CONTRACT (5 ENDPOINTS)

### 3.1 POST /v1/context
**Judge → Bot**: Push new or updated context (category, merchant, customer, trigger).

Request:
```json
{
  "scope": "category" | "merchant" | "customer" | "trigger",
  "context_id": "dentists" | "m_001_drmeera_dentist_delhi" | "c_001_priya" | "trg_001_...",
  "version": 3,
  "payload": {...},
  "delivered_at": "2026-04-26T10:00:00Z"
}
```

Response (200):
```json
{"accepted": true, "ack_id": "ack_abc123", "stored_at": "2026-04-26T10:00:00.123Z"}
```

**Behavior**:
- **Idempotent** by (context_id, version)
- Higher version **replaces** lower version
- Reject stale versions (409 with "stale_version")
- Persist context throughout test

### 3.2 POST /v1/tick
**Judge → Bot**: Periodic wake-up (every 5 simulated minutes). Bot can initiate proactive messages.

Request:
```json
{
  "now": "2026-04-26T10:30:00Z",
  "available_triggers": ["trg_2026_04_26_research_digest", "trg_2026_04_26_recall_priya"]
}
```

Response (200):
```json
{
  "actions": [
    {
      "conversation_id": "conv_001",
      "merchant_id": "m_001_drmeera",
      "customer_id": null,
      "send_as": "vera" | "merchant_on_behalf",
      "trigger_id": "trg_2026_04_26_research_digest",
      "template_name": "vera_research_digest_v1",
      "template_params": ["Dr. Meera", "JIDA Oct issue", ...],
      "body": "Dr. Meera, JIDA's Oct issue landed...",
      "cta": "open_ended" | "yes_no" | "none",
      "suppression_key": "research:dentists:2026-W17",
      "rationale": "External research digest with merchant-relevant clinical anchor..."
    }
  ]
}
```

**Behavior**:
- Can return empty actions (`[]`) if nothing's worth sending
- Generate unique `conversation_id` for new conversations
- Must complete within 30 seconds

### 3.3 POST /v1/reply
**Judge → Bot**: Receive merchant/customer reply; bot responds synchronously.

Request:
```json
{
  "conversation_id": "conv_001",
  "merchant_id": "m_001_drmeera",
  "customer_id": null,
  "from_role": "merchant" | "customer",
  "message": "Yes, send me the abstract",
  "received_at": "2026-04-26T10:45:00Z",
  "turn_number": 2
}
```

Response (200) — one of three actions:

**Action: send**
```json
{
  "action": "send",
  "body": "Sending now — also drafted a 90-sec patient-ed WhatsApp...",
  "cta": "open_ended",
  "rationale": "Honoring the merchant's accept; adding next-best-step..."
}
```

**Action: wait**
```json
{
  "action": "wait",
  "wait_seconds": 1800,
  "rationale": "Merchant asked for time; back off 30 min"
}
```

**Action: end**
```json
{
  "action": "end",
  "rationale": "Merchant said not interested; gracefully exiting"
}
```

**Timeout**: 30 seconds max

### 3.4 GET /v1/healthz
**Judge → Bot**: Liveness probe (every 60s).

Response (200):
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "contexts_loaded": {
    "category": 5,
    "merchant": 50,
    "customer": 200,
    "trigger": 100
  }
}
```

**Penalty**: 3 consecutive failures = disqualification

### 3.5 GET /v1/metadata
**Judge → Bot**: Bot identity and submission info.

Response (200):
```json
{
  "team_name": "Team Alpha",
  "team_members": ["Alice", "Bob"],
  "model": "claude-opus-4-7",
  "approach": "single-prompt composer with retrieval over digest items",
  "contact_email": "team@example.com",
  "version": "1.2.0",
  "submitted_at": "2026-04-26T08:00:00Z"
}
```

---

## 4. SCORING RUBRIC (5 DIMENSIONS)

Each action is scored 0-20 across:

### 4.1 Decision Quality (0-20)
- **20**: Perfect judgment. Right trigger selected, right time, right person.
- **15**: Good judgment. Mostly right, minor timing/person issue.
- **10**: Acceptable. Reasonable but not optimal.
- **5**: Poor judgment. Sent when shouldn't, or missed opportunity.
- **0**: Harmful judgment. Violates consent, taboos, or logic.

**Judged on**:
- Did the bot pick the right trigger?
- Did the bot skip triggers that shouldn't go now?
- Did the bot respect conversation state (wait, end, escalate)?
- Did the bot detect auto-replies and handle appropriately?
- Did the bot recognize merchant intent and route to action?

### 4.2 Specificity (0-20)
- **20**: Concrete numbers, names, sources, dates, precise context.
- **15**: Mostly specific; 1-2 placeholders acceptable.
- **10**: Some specificity; generic language acceptable in parts.
- **5**: Mostly generic; vague claims.
- **0**: No specificity; entirely hallucinated or invented data.

**Judged on**:
- CTR actually in payload (2.1% vs 3.0% peer, not "below average")?
- Merchant name used correctly?
- Research source cited with publication info (JIDA Oct 2026 p.14)?
- Offer prices and titles from catalog, not invented?
- No fabricated revenue, competitor names, research stats?

### 4.3 Category Fit (0-20)
- **20**: Perfect tone, vocabulary, taboos, salutations for category.
- **15**: Good fit; minor tone/vocab issue.
- **10**: Acceptable; some tone/vocab misalignment.
- **5**: Poor fit; tone inappropriate for category.
- **0**: Harmful fit; violates taboos or creates legal risk.

**Judged on**:
- Dentist: peer/clinical tone? No "guaranteed", "cure", "best in city"?
- Salon: service+price or offer relevant? Tone appropriate?
- Pharmacy: clinical language, safety-first messaging?
- Restaurant: value proposition clear? Offer relevant to cuisine/daypart?
- Gym: achievement/motivation tone, retention/engagement focus?

### 4.4 Merchant Fit (0-20)
- **20**: Deeply personalized. Uses merchant name, locality, performance, offers, cohort, signals.
- **15**: Mostly personalized; 1-2 fields missing.
- **10**: Partially personalized; generic in places.
- **5**: Barely personalized; mostly generic.
- **0**: Zero personalization; could have been sent to any merchant.

**Judged on**:
- Merchant name used?
- Performance data used (CTR, calls, views, delta)?
- Customer cohort mentioned (e.g., "high-risk adult patients")?
- Active offers referenced?
- Locality or city mentioned?
- Signals respected (e.g., "stale posts" → prompt to refresh content)?

### 4.5 Engagement Compulsion (0-20)
- **20**: Uses 2+ compulsion levers naturally, strong CTA.
- **15**: Uses 1-2 levers well, clear CTA.
- **10**: Uses 1 lever, acceptable CTA.
- **5**: Weak compulsion; hard or multiple CTAs.
- **0**: No compulsion; likely to be ignored.

**Compulsion Levers**:
1. **Specificity**: concrete numbers, dates, sources
2. **Loss aversion**: "you're missing X", "before window closes"
3. **Social proof**: "3 dentists in your locality did Y"
4. **Effort externalization**: "I've drafted it, just say go"
5. **Curiosity**: "want to see who?", "want the full list?"
6. **Reciprocity**: "I noticed Y, thought you'd want to know"
7. **Asking the merchant**: "what's your most-asked treatment?"
8. **Binary commitment**: YES/STOP, not multi-choice

---

## 5. TRIGGER TYPES (EXAMPLES)

### 5.1 External Triggers (happening outside the merchant's account)
- `festival_upcoming`: Diwali in 4 days → seasonal opportunity
- `weather_event`: Heatwave 42°C → timely messaging
- `local_news_event`: Expressway closed → urgency
- `research_digest`: JIDA issue dropped → clinical/knowledge opportunity
- `regulation_change`: DCI radiograph limits revised → compliance alert
- `competitor_opened`: New dentist 1.3km away → threat/opportunity
- `trend_movement`: Clear aligners searches +62% YoY → demand signal

### 5.2 Internal Triggers (happening within merchant's data)
- `perf_spike`: Views +28% yesterday → momentum/repeatability
- `perf_dip`: Calls -40% WoW → problem solving
- `milestone`: 100 reviews crossed → celebration/engagement
- `dormant`: No message in 14 days → re-engagement
- `customer_lapsed_soft`: Recall window opens → winback
- `appointment_tomorrow`: Booking exists → reminder
- `review_theme`: "wait time" in 3 reviews → reputation management
- `scheduled_recurring`: Weekly Friday curious-ask → habit

---

## 6. KEY ANTI-PATTERNS (JUDGE PENALIZES)

1. **Generic offers**: "Flat 30% off" → "Haircut @ ₹99" (specific, from catalog)
2. **Multiple CTAs**: "Reply YES for X, NO for Y, MAYBE for Z" → single binary
3. **Buried CTA**: Action should land in last sentence
4. **Wrong tone**: Promotional "AMAZING!" for dentist → peer/clinical
5. **Hallucinated data**: Citing "JIDA paper" not in digest → only use what's present
6. **Long preamble**: "I hope you're doing well..." → direct value
7. **Self-reintroduction**: After first message, assume merchant knows you
8. **Language mismatch**: Hindi merchant getting pure English → use language pref
9. **Verbatim repetition**: Same message sent before in same conversation → anti-repetition
10. **Intent miss**: Merchant says "Yes, do it" and you ask "What audience?" → route to action

---

## 7. CRITICAL FEATURES TO IMPLEMENT

### 7.1 Context Versioning
- Accept first version of any (scope, context_id)
- Accept newer version; ignore/reject stale
- Never replace newer with older
- Make new context immediately available

### 7.2 Suppression
Prevent repeated messaging for same trigger:
- Use suppression_key from trigger (e.g., "research:dentists:2026-W17")
- Track per conversation or globally
- Example: don't send same research digest twice to same merchant in one window

### 7.3 Auto-Reply Detection
Detect automated WhatsApp Business replies:
- Same message verbatim 3+ times → auto-reply
- "Thank you for contacting", "Our team will get back", "automated response"
- When detected: ask at most 1 routing question, then end (don't burn 3+ turns)

### 7.4 Intent Recognition
When merchant says:
- **Yes-intent**: "yes", "sure", "go ahead", "kar do", "haan" → route to action immediately
- **No-intent**: "no", "not interested", "stop", "remove me" → end conversation gracefully
- **Wait-intent**: "later", "tomorrow", "I'm busy" → use wait action

### 7.5 Conversation State Machine
States:
- `initiated` → awaiting merchant response
- `merchant_replied` → process and respond
- `intent_action` → merchant said yes → move to execution
- `waiting` → merchant asked for time → back off
- `ended` → merchant said no or 3 unanswered → stop
- `escalated` → unclear → hand off or stop

### 7.6 Category-Specific Behavior
For each category (dentists, salons, restaurants, gyms, pharmacies):
- Approved tone, vocabulary, taboos
- Common merchant problems (from brief)
- Relevant customer lifecycle
- Appropriate CTAs
- Research relevance
- Offer relevance

**Example - Dentists**:
- Tone: peer/clinical, respectful
- Vocabulary: fluoride, scaling, caries, endodontic, aligner, veneer, OPG, IOPA, RCT
- Taboos: guaranteed, cure, 100% safe, "best in city"
- Common problems: low recall compliance, stale posts, competition from clear aligners
- CTA style: "Want me to draft patient-ed?", "Want me to check your recall schedule?"

---

## 8. MERCHANT PERSONALIZATION FIELDS

Use when available (never invent):
- Merchant name
- Locality and city
- Category
- Views, calls, directions (30d)
- CTR (vs peer benchmark)
- Performance change (7d delta)
- Peer benchmark (from category)
- Active offer title and price
- Reviews and review themes
- Merchant signals (stale_posts, dormant, ctr_below_peer, etc.)
- Customer cohort (e.g., "high_risk_adult_count": 124)
- Previous conversation engagement

**Anti-Example**:
```
"Grow your business today!" ❌

Better:
"Your CTR is 2.1% vs a 3.0% peer average. Want me to suggest one profile change?" ✓
```

---

## 9. CONSENT & CUSTOMER OUTREACH

### 9.1 Consent is a Hard Gate
Before contacting a customer:
1. Check customer context exists
2. Check consent.scope includes intended action
3. Allowed scopes: ["recall_reminders", "appointment_reminders", "promotional_offers", ...]
4. If scope is empty or absent → do not send customer outreach

### 9.2 send_as Field
- `"vera"`: Vera sends message to merchant
- `"merchant_on_behalf"`: Vera drafts message for merchant to send to customer (with explicit consent)

---

## 10. DATASET STRUCTURE (PROVIDED)

**Categories** (5 files in `/dataset/categories/`):
- dentists.json
- salons.json
- restaurants.json
- gyms.json
- pharmacies.json

**Seed Data** (expandable by judge):
- merchants_seed.json: 10 merchants/category × 5 categories = 50 base
- customers_seed.json: 15 customers, related to merchants
- triggers_seed.json: 25 triggers spanning all types

**Generator**:
- generate_dataset.py: expands seed to full test dataset (50→200 merchants, etc.)
- Judge may inject additional contexts mid-test

---

## 11. TESTING & EVALUATION

### 11.1 Judge Simulator
Run locally before submission:
```bash
python judge_simulator.py
```

Provides:
- Simulated merchant replies (using LLM to play merchant role)
- Score on each action across 5 dimensions
- Qualitative feedback
- Failure detection

### 11.2 Test Phases (From Brief)
1. **Baseline**: All canonical triggers with base merchants/customers
2. **Robustness**: New merchants, new customers, unknown triggers
3. **Conversation**: Multi-turn depth, intent transitions
4. **Replay**: Variations injected mid-test, dynamic context
5. **Comparison**: Top-scorer benchmarking

### 11.3 Failure Modes & Penalties

| Failure | Penalty |
|---------|---------|
| Healthz fails 3× | -10 (disqualified) |
| Tick/reply timeouts (>30s) | -1 per timeout |
| Malformed JSON | -2 per response |
| Empty body in "send" action | -2 |
| Verbatim repetition in conversation | -2 per repeat |
| Stale version accepted | -1 |
| Consent violation (customer outreach without consent) | -5 |

---

## 12. PROJECT STRUCTURE (RECOMMENDED)

```
vera-challenge/
├── app.py                    # FastAPI entry point
├── engine/
│   ├── __init__.py
│   ├── context_store.py      # Context versioning + persistence
│   ├── trigger_ranker.py     # Trigger scoring + selection
│   ├── decision_engine.py    # Decision routing
│   ├── message_planner.py    # Message composition strategy
│   ├── composer.py           # LLM/template-based composition
│   ├── conversation.py       # Conversation state machine
│   ├── validation.py         # Output schema validation
│   ├── intent.py             # Intent recognition (yes/no/wait)
│   ├── auto_reply.py         # Auto-reply detection
│   └── consent.py            # Consent checking
├── models/
│   ├── context.py            # Pydantic schemas
│   ├── response.py           # API response models
│   └── types.py              # Enums, constants
├── data/
│   ├── categories.py         # Load + cache category data
│   └── seeds.py              # Load seed data for reference
├── tests/
│   ├── test_context.py
│   ├── test_trigger_ranking.py
│   ├── test_consent.py
│   ├── test_intent.py
│   ├── test_auto_reply.py
│   ├── test_message_quality.py
│   └── test_api_contract.py
├── scripts/
│   ├── run_judge_simulator.sh
│   └── local_test.py
├── reports/
│   └── baseline-report.md
├── docs/
│   ├── architecture.md
│   ├── decision-engine.md
│   └── testing.md
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .env.example
├── .gitignore
├── README.md
└── start.sh
```

---

## 13. ENVIRONMENT VARIABLES

```env
TEAM_NAME=Team Alpha
TEAM_MEMBERS=Alice,Bob
CONTACT_EMAIL=team@example.com
BOT_VERSION=1.0.0

# Optional: if using LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-4-7
LLM_API_KEY=sk-...
```

---

## 14. DEPLOYMENT

### 14.1 Local Development
```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8080
```

### 14.2 Docker
```bash
docker build -t vera-bot .
docker run -p 8080:8080 -e PORT=8080 vera-bot
```

### 14.3 Public Deployment (Render)
```bash
git push heroku main
# or
# Upload to Render dashboard with render.yaml
```

Public URL: `https://vera-bot-<team>.onrender.com`

---

## 15. SUBMISSION CHECKLIST

- [ ] All 5 endpoints implemented
- [ ] Context versioning works (idempotent, stale rejection)
- [ ] Conversation state persisted correctly
- [ ] Trigger ranking deterministic and grounded
- [ ] Message generation uses real data only (no hallucinations)
- [ ] Auto-reply detection implemented
- [ ] Intent recognition (yes/no/wait)
- [ ] Consent checking for customer outreach
- [ ] Suppression prevents repeated messages
- [ ] Output validation (schema, no repetition)
- [ ] Category-specific behavior for all 5 categories
- [ ] Merchant personalization across all fields
- [ ] No hardcoded canonical test cases
- [ ] Unit tests passing
- [ ] Judge simulator passing with non-zero scores
- [ ] Docker build successful
- [ ] Public endpoint reachable
- [ ] .env.example provided (no secrets in repo)
- [ ] README with full setup/deployment instructions
- [ ] Submitted URL via portal

---

## 16. NEXT STEPS

**STEP 1**: Read engagement-design.md and engagement-research.md (§17-18 below)  
**STEP 2**: Review examples (api-call-examples.md, case-studies.md)  
**STEP 3**: Implement API skeleton (all 5 endpoints, basic responses)  
**STEP 4**: Implement context store (versioning, persistence)  
**STEP 5**: Implement trigger ranker  
**STEP 6**: Implement message composition (category-aware, merchant-personalized)  
**STEP 7**: Implement conversation state machine  
**STEP 8**: Run unit tests  
**STEP 9**: Run judge simulator  
**STEP 10**: Fix failures, iterate  

---

## 17. ENGAGEMENT DESIGN SUMMARY

(See engagement-design.md for full details)

Key principles:
- **Specificity > hype**: 2,100-patient trial > "amazing new research"
- **Loss aversion**: "Before this window closes...", "You're missing X"
- **Social proof**: "3 dentists in Lajpat Nagar did this"
- **Effort externalization**: "I've drafted it—just review"
- **Curiosity**: "Want to see who?", "Want the full list?"
- **Ask the merchant**: Engage their expertise
- **Single binary**: YES/STOP, not multi-choice

Merchant's biggest missing engagement today: **social proof** and **asking the merchant**—barely fire, high upside.

---

## 18. RESEARCH CONTEXT

(See engagement-research.md for full details)

Categories + their research drivers:
- **Dentists**: JIDA, DCI, IDA, clinical trials, regulatory changes
- **Salons**: Bridal/festival demand, beauty trends, regional preferences
- **Restaurants**: Food trends, local events, daypart optimization
- **Gyms**: Fitness trends, seasonal (New Year), corporate wellness
- **Pharmacies**: Drug regulatory updates, health alerts, OTC demand

Use research/digest items to anchor curiosity.

---

## 19. FINAL NOTES

1. **Official spec wins**: If challenge-brief or challenge-testing-brief conflicts with this document, follow the official brief.
2. **No hallucinations**: Every number, name, source must come from context pushed by judge.
3. **Generalize, don't hardcode**: Build rules, not test-case handlers.
4. **Respect the merchant**: Vera works for them; don't waste their time.
5. **Listen to the customer**: If they opt out, stop.
6. **Be clever, not clever-sounding**: Depth, specificity, judgment over wordsmithing.

---

**End of Challenge Understanding**
