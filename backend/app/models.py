import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScoredResponse(Base):
    """
    One scored LLM response, matching the WebSocket/REST payload schema
    documented in the build plan (Section 2.4). This is the single
    source of truth both endpoints serialize from.
    """

    __tablename__ = "scored_responses"

    id = Column(String, primary_key=True, default=new_id)
    session_id = Column(String, index=True, default="demo-session")
    model = Column(String, default="default")
    use_case = Column(String, default="customer_support")
    geography = Column(String, default="US")
    timestamp = Column(DateTime, default=utcnow)

    prompt_excerpt = Column(String)
    response_excerpt = Column(String)

    # Check results, stored as JSON blobs matching the documented schema
    performance = Column(JSON)
    cost = Column(JSON)
    responsibility = Column(JSON)
    bias = Column(JSON)
    hallucination = Column(JSON)
    correlation = Column(JSON)

    severity = Column(String, default="pass")  # pass | edit | log | block
    decision_reason = Column(String, default="")
    original_severity = Column(String, nullable=True)
    original_decision_reason = Column(String, nullable=True)

    # Feedback & Overrides
    override_status = Column(
        String, default="none"
    )  # none | override_allow | override_block
    override_reason = Column(String, nullable=True)
    feedback_text = Column(String, nullable=True)
    feedback_entries = relationship(
        "FeedbackEntry", back_populates="response", cascade="all, delete-orphan"
    )

    def to_payload(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "model": self.model,
            "use_case": self.use_case,
            "geography": self.geography,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "prompt": self.prompt_excerpt,
            "response": self.response_excerpt,
            "checks": {
                "performance": self.performance,
                "cost": self.cost,
                "responsibility": self.responsibility,
                "bias": self.bias,
                "hallucination": self.hallucination,
            },
            "correlation": self.correlation,
            "severity": self.severity,
            "decision_reason": self.decision_reason,
            "original_severity": self.original_severity or self.severity,
            "original_decision_reason": self.original_decision_reason
            or self.decision_reason,
            "override_status": self.override_status,
            "override_reason": self.override_reason,
            "feedback_text": self.feedback_text,
            "feedback": [
                {
                    "id": entry.id,
                    "override": entry.override,
                    "note": entry.note,
                    "timestamp": entry.timestamp.isoformat(),
                }
                for entry in self.feedback_entries
            ],
        }


class FeedbackEntry(Base):
    """Human evaluation captured for later threshold recalibration."""

    __tablename__ = "feedback_entries"

    id = Column(String, primary_key=True, default=new_id)
    response_id = Column(String, ForeignKey("scored_responses.id"), index=True)
    override = Column(String)
    note = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

    response = relationship("ScoredResponse", back_populates="feedback_entries")
