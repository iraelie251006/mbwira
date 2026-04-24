# Mbwira — Architecture

## One-page system overview

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    USSD     │   │  WhatsApp   │   │     Web     │
│  (any phone)│   │  (Android)  │   │  (anyone)   │
│ Africa's Tk │   │ Meta Cloud  │   │   mbwira.rw │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                  │
       ▼                 ▼                  ▼
 ┌───────────────────────────────────────────────┐
 │              FastAPI Application              │
 │                                               │
 │  /ussd    /whatsapp   /chat    /counselor     │
 │    │         │          │           ▲         │
 │    │         │          │           │         │
 │    ▼         ▼          ▼           │         │
 │  ┌──────────────────────────┐       │         │
 │  │      Decision engine     │       │         │
 │  │                          │       │         │
 │  │  [USSD menu tree]  OR    │       │         │
 │  │  [Claude + history]      │       │         │
 │  └────────────┬─────────────┘       │         │
 │               ▼                     │         │
 │      ┌────────────────┐             │         │
 │      │  Safety layer  │─────────────┤         │
 │      │                │  escalate   │         │
 │      │ - pre keywords │  triggers   │         │
 │      │ - post tag     │  queue an   │         │
 │      └────────────────┘  Escalation │         │
 │                                     │         │
 │  ┌────────────────────────────────────────┐   │
 │  │      PostgreSQL / SQLite (SQLAlchemy)  │   │
 │  │                                        │   │
 │  │  sessions · messages · escalations     │   │
 │  │  counselors                            │   │
 │  └────────────────────────────────────────┘   │
 └───────────────────────────────────────────────┘
```

## Data model

Four tables, intentionally minimal:

**sessions** — anonymous conversation containers. Never stores raw phone numbers; only a SHA-256 `phone_hash` for continuity (so a returning WhatsApp user lands in the same conversation).

**messages** — every turn, flagged if the safety layer found a signal. Used for history + auditing.

**escalations** — one per session when a human is needed. `level` is `counselor`, `chw`, or `emergency`. Status flows `pending → taken → resolved`.

**counselors** — staff accounts (not used in MVP login, but ready for per-counselor assignment in the next iteration).

## Safety model (defense in depth)

1. **Pre-filter** on every incoming user message (deterministic, <1ms):
   - Keyword lists in Kinyarwanda and English for suicide, GBV, medical emergencies
   - Regex for age patterns that may indicate child safeguarding cases

2. **Prompted model behavior**: Claude's system prompt includes hard rules:
   - Never diagnose, never prescribe
   - Prefix any response to a crisis disclosure with `[ESCALATE: reason]`
   - Always include hotlines in crisis responses

3. **Post-filter** on every LLM reply: regex extracts the `[ESCALATE: reason]` tag, strips it from the user-facing reply, and creates an Escalation.

If either layer fires, the reply is augmented with Rwandan hotline info (112, 114, 3029) and a counselor handoff is queued.

## Privacy design

- **No account creation.** Users are identified only by session ID (web), phone hash (WhatsApp), or session ID (USSD).
- **Minimal retention.** Plan: auto-purge message bodies after 30 days; keep only aggregated analytics.
- **No identifying data surfaced to counselors.** The dashboard shows transcript + channel, not phone numbers.
- **Transport security.** HTTPS in production, WhatsApp Business API is E2E for user↔Meta leg; our leg Meta↔server is TLS.
- **Rwandan data residency.** Production deployment targets AWS Africa (Cape Town) or a Kigali-based provider.

## Scaling plan

| Load                  | Action                                             |
|-----------------------|----------------------------------------------------|
| 0–1k users/day        | SQLite + single uvicorn worker (current MVP)       |
| 1k–50k users/day      | Postgres, gunicorn+uvicorn, horizontal scale       |
| 50k+                  | Move to Supabase/RDS, move LLM calls behind a queue|

The USSD menu tree runs entirely in-memory and costs nothing to scale. The bottleneck is the LLM cost on WhatsApp/web — mitigated by keeping conversation history short (last 20 messages) and using the cheapest Claude tier that meets quality bar.

## Integration roadmap

| Integration                    | What it unlocks                                      |
|--------------------------------|------------------------------------------------------|
| MoH HMIS                       | Aggregated (anonymized) trend reporting to ministry  |
| Community Health Worker app    | CHW-initiated escalations, home visit coordination   |
| Mutuelle de Santé              | Paid-tier counseling sessions reimbursed             |
| Isange One Stop Centers        | Warm transfer for GBV cases                          |
| Rwanda Biomedical Centre       | Clinical content validation & regular review         |
