"""
WhatsApp Cloud API webhook.

Setup:
- Verify token challenge on GET (Meta handshake).
- On POST, receive incoming messages, echo through the same chat pipeline
  used by the web endpoint, send reply via WhatsApp API.

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
"""
import hashlib
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import Session as DBSession, Message, get_db
from app.services.llm import ask_claude
from app.services.safety import (
    check_user_message,
    extract_escalation_from_response,
    safety_response_text,
)
from app.services.handoff import create_escalation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

WHATSAPP_API_URL = "https://graph.facebook.com/v25.0"


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


async def _get_or_create_session(db: AsyncSession, phone: str) -> DBSession:
    phone_hash = _hash_phone(phone)
    # Use phone hash as the session ID for WhatsApp so conversations continue
    sid = f"wa_{phone_hash[:24]}"
    q = await db.execute(select(DBSession).where(DBSession.session_id == sid))
    sess = q.scalar_one_or_none()
    if sess:
        return sess
    sess = DBSession(
        session_id=sid,
        channel="whatsapp",
        phone_hash=phone_hash,
        contact_number=phone,  # they've already messaged us — we have their number
        language="rw",
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


async def _send_whatsapp(phone: str, text: str) -> None:
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp not configured; would have sent: %s", text[:100])
        return
    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 300:
            logger.error("WhatsApp send failed: %s %s", r.status_code, r.text)


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(403, "Verification failed")


@router.post("")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    logger.info("WhatsApp webhook payload: %s", payload)

    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages") or []
        if not messages:
            # Could be a status update (delivered/read), not a message
            return {"ok": True}
        msg = messages[0]
        from_phone = msg["from"]
        if msg.get("type") != "text":
            await _send_whatsapp(
                from_phone,
                "Mbabarira, ubu nakira amagambo gusa. / Sorry, I can only read text for now.",
            )
            return {"ok": True}
        text = msg["text"]["body"]
    except (KeyError, IndexError) as exc:
        logger.warning("Malformed WhatsApp payload: %s", exc)
        return {"ok": True}

    sess = await _get_or_create_session(db, from_phone)

    # Pre-check
    pre_signal = check_user_message(text)
    db.add(Message(
        session_id=sess.id,
        role="user",
        content=text,
        flagged=pre_signal.triggered,
        flag_reason=pre_signal.reason,
    ))
    await db.commit()

    # Build history
    q = await db.execute(
        select(Message)
        .where(Message.session_id == sess.id)
        .order_by(Message.created_at.asc())
        .limit(20)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in q.scalars()
        if m.role in ("user", "assistant")
    ]

    reply = await ask_claude(history)
    post_reason, cleaned = extract_escalation_from_response(reply)
    final_reason = pre_signal.reason or post_reason
    if final_reason:
        cleaned = cleaned + safety_response_text(final_reason, sess.language)
        await create_escalation(
            db, sess, reason=final_reason,
            level="emergency" if final_reason == "medical_emergency" else "counselor",
            notes=f"WhatsApp: {text[:200]}",
        )

    db.add(Message(
        session_id=sess.id,
        role="assistant",
        content=cleaned,
        flagged=bool(final_reason),
        flag_reason=final_reason,
    ))
    await db.commit()

    await _send_whatsapp(from_phone, cleaned)
    return {"ok": True}
