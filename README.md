# Mbwira

**Ubuzima bwawe, ibanga ryawe.** A confidential Kinyarwanda health companion for young Rwandans — accessible via USSD, WhatsApp, and web — covering sexual and reproductive health and mental health, with safe escalation to licensed counselors.

Built for the [iAccelerator 2026](https://ia.imbutofoundation.org/) competition (Imbuto Foundation · MINIYOUTH · UNFPA).

---

## What's in the box

```
mbwira/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI entry point
│       ├── config.py                # env-based settings
│       ├── routers/
│       │   ├── ussd.py              # Africa's Talking USSD webhook
│       │   ├── whatsapp.py          # Meta WhatsApp webhook
│       │   ├── chat.py              # web chat API
│       │   └── counselor.py         # counselor dashboard API
│       ├── services/
│       │   ├── llm.py               # Claude API wrapper
│       │   ├── safety.py            # crisis keyword + escalation detection
│       │   └── handoff.py           # creates Escalation records
│       ├── content/
│       │   ├── ussd_tree.py         # bilingual menu tree (Kinyarwanda/English)
│       │   └── system_prompt.py     # Claude instructions for WhatsApp/web
│       └── models/db.py             # SQLAlchemy models (Session, Message, Escalation)
├── frontend/
│   ├── index.html                   # public landing page
│   ├── chat.html                    # web chat demo
│   ├── ussd_simulator.html          # browser-based USSD phone simulator
│   └── counselor.html               # counselor dashboard
└── docs/
    ├── ARCHITECTURE.md
    ├── PITCH.md
    └── SETUP.md
```

---

## Quickstart (local, ~5 minutes)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — at minimum set ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Then open:
- **http://localhost:8000** — landing page
- **http://localhost:8000/ussd-sim** — USSD simulator (best demo for judges)
- **http://localhost:8000/chat-ui** — web chat
- **http://localhost:8000/dashboard** — counselor dashboard (password from `.env`)
- **http://localhost:8000/docs** — auto-generated API docs

---

## How each channel works

### USSD (`POST /ussd`)
Africa's Talking sends `sessionId`, `serviceCode`, `phoneNumber`, `text`. We walk the decision tree in `content/ussd_tree.py` and return `"CON ..."` or `"END ..."`. Screens that represent crisis moments (e.g. `mh_suicidal`) automatically create an `Escalation` record.

### WhatsApp (`POST /whatsapp`)
Meta Cloud API webhook. Incoming text goes through the pre-safety-filter → Claude → post-safety-filter → persistence → reply via Meta's send-message API. Session keyed by hashed phone number so conversations continue.

### Web chat (`POST /chat`)
Same pipeline as WhatsApp, but with an explicit `session_id` issued by `GET /chat/new`. Used by the frontend and for testing.

### Counselor dashboard
Password-protected endpoints under `/counselor/*`. Lists pending escalations, shows full conversation history, lets a counselor mark resolved with notes.

---

## The safety model

Two-layer defense so no crisis signal is missed:

1. **Pre-filter** (`services/safety.py`) — keyword + regex scan of the incoming user message. Catches obvious signals (suicide, GBV, medical emergency) in Kinyarwanda and English.
2. **Post-filter** — Claude's system prompt requires it to prefix urgent responses with `[ESCALATE: reason]`. We extract that tag before sending the reply and create an escalation.

Either path triggers the same handoff flow.

---

## What judges should test

1. **USSD simulator** — click the "Menu → 2 → 5" quick-dial to see the self-harm escalation flow.
2. **Web chat** — try: "I think I want to end my life" (English) or "ndashaka kwiyahura" (Kinyarwanda). Watch it escalate.
3. **Counselor dashboard** — log in, see the escalation appear in real time, open it, read the transcript, resolve it.

---

## Tech choices and why

| Choice                   | Why                                                           |
|--------------------------|---------------------------------------------------------------|
| FastAPI                  | Fast to build, async for chat, great OpenAPI docs             |
| SQLite (dev) / Postgres  | Zero-config for MVP, clean upgrade path to Supabase/RDS       |
| Claude API               | Best Kinyarwanda handling among major LLMs; strong safety     |
| Africa's Talking         | Rwanda coverage, sandbox is free, same API for USSD+SMS       |
| Meta WhatsApp Cloud API  | Official, reliable, free for incoming                         |
| Vanilla HTML/CSS/JS      | Small surface for a demo, fast to load on 2G/3G               |

---

## What this is NOT (yet)

This is an MVP for the iAccelerator pitch. It is not production ready. Before going live with real users we need:

- Native-speaker clinical review of all Kinyarwanda content
- Licensed clinical advisor(s) on-call for escalations
- Signed data-processing agreement with MoH / RBC
- Rwandan data protection law (Law N° 058/2021) compliance review
- Penetration test of the counselor dashboard
- Real Africa's Talking short-code (not sandbox)
- Meta WhatsApp Business verification

See [docs/SETUP.md](docs/SETUP.md) for the checklist.

---

## License & Contact

Built by [Your Name] for the iAccelerator 2026 competition.
All content drafts require clinical review before live deployment.
