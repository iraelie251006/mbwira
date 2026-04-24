"""Database models. Keep data minimal — anonymity is the product."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


class Session(Base):
    """A user conversation session. No PII — only a random session_id and channel."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(16))  # 'ussd' | 'whatsapp' | 'web'
    # Hashed phone token for session continuity (never shown to anyone).
    phone_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Raw contact number, stored ONLY for escalation callback. Encrypted at rest
    # in production (see services/crypto.py). Only revealed via audited dashboard action.
    contact_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="rw")  # 'rw' | 'en'
    topic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    escalation: Mapped["Escalation | None"] = relationship(back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # 'user' | 'assistant' | 'system'
    content: Mapped[str] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[Session] = relationship(back_populates="messages")


class Escalation(Base):
    """When a user needs a human — counselor, CHW, or emergency services."""
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True)
    level: Mapped[str] = mapped_column(String(16))  # 'counselor' | 'chw' | 'emergency'
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | taken | resolved
    counselor_id: Mapped[int | None] = mapped_column(
        ForeignKey("counselors.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    session: Mapped[Session] = relationship(back_populates="escalation")
    counselor: Mapped["Counselor | None"] = relationship()


class Counselor(Base):
    __tablename__ = "counselors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    credentials: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str] = mapped_column(String(64))  # 'srh' | 'mental_health' | 'both'
    phone: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ------- engine / session factory -------
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
