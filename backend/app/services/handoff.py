"""Create escalations when a user needs human help."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Escalation, Session

logger = logging.getLogger(__name__)


async def create_escalation(
    db: AsyncSession,
    session: Session,
    reason: str,
    level: str = "counselor",
    notes: str | None = None,
) -> Escalation:
    """Create or update an escalation for a session."""
    # Idempotent: if already escalated with same reason, don't duplicate.
    existing = await db.execute(
        select(Escalation).where(Escalation.session_id == session.id)
    )
    existing = existing.scalar_one_or_none()
    if existing and existing.status == "pending":
        return existing

    escalation = Escalation(
        session_id=session.id,
        level=level,
        reason=reason,
        status="pending",
        notes=notes,
    )
    db.add(escalation)
    session.escalated = True
    await db.commit()
    await db.refresh(escalation)
    logger.warning(
        "Escalation created: session=%s reason=%s level=%s",
        session.session_id, reason, level,
    )
    return escalation
