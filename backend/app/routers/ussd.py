"""
USSD endpoint compatible with Africa's Talking.

Africa's Talking POSTs form fields:
  sessionId, serviceCode, phoneNumber, text

We must return plain text starting with 'CON ' (continue) or 'END ' (close).
Docs: https://developers.africastalking.com/docs/ussd/overview
"""
import hashlib
import logging
from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Session as DBSession, Message, get_db
from app.content.ussd_tree import walk_tree
from app.services.handoff import create_escalation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ussd", tags=["ussd"])


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


async def _get_or_create_session(
    db: AsyncSession, session_id: str, phone_hash: str, phone: str
) -> DBSession:
    q = await db.execute(select(DBSession).where(DBSession.session_id == session_id))
    sess = q.scalar_one_or_none()
    if sess:
        return sess
    sess = DBSession(
        session_id=session_id,
        channel="ussd",
        phone_hash=phone_hash,
        contact_number=phone,  # carrier already gave us the number
        language="rw",
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


@router.post("")
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(""),
    phoneNumber: str = Form(""),
    text: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> Response:
    phone_hash = _hash_phone(phoneNumber) if phoneNumber else ""
    db_session = await _get_or_create_session(db, sessionId, phone_hash, phoneNumber)

    # Walk the tree based on accumulated input
    state, screen = walk_tree(text, lang="rw")  # default Kinyarwanda
    prompt = screen["prompt"]
    kind = screen["type"]  # 'CON' or 'END'

    # Log the final interaction for auditing
    db.add(Message(
        session_id=db_session.id,
        role="user",
        content=f"[USSD input: {text!r} -> state: {state}]",
    ))
    db.add(Message(
        session_id=db_session.id,
        role="assistant",
        content=prompt,
    ))
    db_session.topic = state

    # Trigger escalation if this screen requests it
    escalation_reason = screen.get("triggers_escalation")
    if escalation_reason:
        await create_escalation(
            db, db_session, reason=escalation_reason, level="counselor",
            notes=f"Escalated from USSD state '{state}'",
        )

    await db.commit()

    body = f"{kind} {prompt}"
    return Response(content=body, media_type="text/plain")
