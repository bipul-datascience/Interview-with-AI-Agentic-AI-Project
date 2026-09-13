"""SQLAlchemy persistence for users, resumes, interview sessions, and progress."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from services.crypto import decrypt_text, encrypt_text

load_dotenv()


class DatabaseConfigurationError(RuntimeError):
    pass


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    interviews: Mapped[list["InterviewSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    encrypted_text: Mapped[str] = mapped_column(Text)
    encrypted_assessment: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id"))
    target_role: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(30))
    interview_style: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    encrypted_job_description: Mapped[str] = mapped_column(Text)
    encrypted_state: Mapped[str] = mapped_column(Text)
    encrypted_final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="interviews")


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise DatabaseConfigurationError("DATABASE_URL is required for Phase 2. Start PostgreSQL with docker compose and add the connection string to .env.")
    return value


def _engine():
    return create_engine(database_url(), pool_pre_ping=True)


def init_database() -> None:
    Base.metadata.create_all(_engine())


@contextmanager
def session_scope():
    factory = sessionmaker(bind=_engine(), expire_on_commit=False)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_resume(*, user_id: int, filename: str, text: str, assessment: dict) -> Resume:
    resume = Resume(user_id=user_id, filename=filename, encrypted_text=encrypt_text(text), encrypted_assessment=encrypt_text(assessment))
    with session_scope() as db:
        db.add(resume)
        db.flush()
        return resume


def create_interview(*, user_id: int, resume_id: str, role: str, difficulty: str, interview_style: str, job_description: str, state: dict) -> InterviewSession:
    interview = InterviewSession(user_id=user_id, resume_id=resume_id, target_role=role, difficulty=difficulty, interview_style=interview_style, encrypted_job_description=encrypt_text(job_description), encrypted_state=encrypt_text(state))
    with session_scope() as db:
        db.add(interview)
        db.flush()
        return interview


def update_interview(*, interview_id: str, user_id: int, state: dict) -> None:
    with session_scope() as db:
        interview = db.scalar(select(InterviewSession).where(InterviewSession.id == interview_id, InterviewSession.user_id == user_id))
        if not interview:
            raise ValueError("Interview session not found.")
        interview.encrypted_state = encrypt_text(state)
        interview.status = state.get("status", "active")
        if state.get("final_report"):
            interview.encrypted_final_report = encrypt_text(state["final_report"])
        if interview.status == "complete" and not interview.ended_at:
            interview.ended_at = now_utc()


def list_interviews(user_id: int) -> list[InterviewSession]:
    with session_scope() as db:
        return list(db.scalars(select(InterviewSession).where(InterviewSession.user_id == user_id).order_by(InterviewSession.updated_at.desc())))


def load_interview(*, interview_id: str, user_id: int) -> dict:
    with session_scope() as db:
        interview = db.scalar(select(InterviewSession).where(InterviewSession.id == interview_id, InterviewSession.user_id == user_id))
        if not interview:
            raise ValueError("Interview session not found.")
        return {"id": interview.id, "state": decrypt_text(interview.encrypted_state), "report": decrypt_text(interview.encrypted_final_report) if interview.encrypted_final_report else None, "started_at": interview.started_at}


def progress_summary(user_id: int) -> dict:
    sessions = list_interviews(user_id)
    completed = [item for item in sessions if item.status == "complete" and item.encrypted_final_report]
    scores = [decrypt_text(item.encrypted_final_report).get("overall_score", 0) for item in completed]
    return {"total": len(sessions), "completed": len(completed), "active": len([item for item in sessions if item.status == "active"]), "average_score": round(sum(scores) / len(scores), 1) if scores else None}
