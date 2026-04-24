"""
Web chat endpoint. Used by the public demo page and for testing.

POST /chat with { session_id: string, message: string } -> { reply, escalated }
GET  /chat/new creates a new anonymous session id.
"""
import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Session as DBSession, Message, get_db
from app.services.llm import ask_claude
from app.services.safety import (
    check_user_message,
    extract_escalation_from_response,
    safety_response_text,
)
from app.services.handoff import create_escalation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class NewSessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: str = "rw"


class ChatResponse(BaseModel):
    reply: str
    escalated: bool
    escalation_reason: str | None = None


@router.get("/new", response_model=NewSessionResponse)
async def new_session(db: AsyncSession = Depends(get_db)) -> NewSessionResponse:
    sid = "web_" + secrets.token_urlsafe(16)
    sess = DBSession(session_id=sid, channel="web")
    db.add(sess)
    await db.commit()
    return NewSessionResponse(session_id=sid)


async def _load_session(db: AsyncSession, session_id: str) -> DBSession:
    q = await db.execute(select(DBSession).where(DBSession.session_id == session_id))
    sess = q.scalar_one_or_none()
    if not sess:
        raise HTTPException(404, "Session not found. Start a new session.")
    return sess


async def _load_history(db: AsyncSession, session_pk: int, limit: int = 20) -> list[dict]:
    q = await db.execute(
        select(Message)
        .where(Message.session_id == session_pk)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list(q.scalars())[::-1]  # chronological
    return [
        {"role": m.role, "content": m.content}
        for m in rows
        if m.role in ("user", "assistant")
    ]


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    sess = await _load_session(db, req.session_id)
    sess.language = req.language or "rw"

    # 1. Pre-check user message for crisis signals
    pre_signal = check_user_message(req.message)

    # 2. Persist user message
    user_msg = Message(
        session_id=sess.id,
        role="user",
        content=req.message,
        flagged=pre_signal.triggered,
        flag_reason=pre_signal.reason,
    )
    db.add(user_msg)
    await db.commit()

    # 3. Build conversation history and ask Claude
    history = await _load_history(db, sess.id)
    # Add current user message (it's already saved, but ensure it's in the history)
    if not history or history[-1]["role"] != "user":
        history.append({"role": "user", "content": req.message})

    reply_text = await ask_claude(history)

    # 4. Post-check LLM output
    post_reason, cleaned_reply = extract_escalation_from_response(reply_text)

    # Combine pre and post signals
    final_reason = pre_signal.reason or post_reason
    escalated = bool(final_reason)

    # Append safety tail text if we have a reason
    if final_reason:
        cleaned_reply = cleaned_reply + safety_response_text(final_reason, req.language)

    # 5. Save assistant reply
    db.add(Message(
        session_id=sess.id,
        role="assistant",
        content=cleaned_reply,
        flagged=escalated,
        flag_reason=final_reason,
    ))
    await db.commit()

    # 6. Create escalation if needed
    if escalated:
        await create_escalation(
            db, sess, reason=final_reason or "unknown",
            level="emergency" if final_reason == "medical_emergency" else "counselor",
            notes=f"Auto-detected from chat: {req.message[:200]}",
        )

    return ChatResponse(
        reply=cleaned_reply,
        escalated=escalated,
        escalation_reason=final_reason,
    )
