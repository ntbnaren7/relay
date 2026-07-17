"""SQLAlchemy 2.0 Declarative ORM models for jobs and steps."""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Root declarative base class."""
    pass


class JobRecord(Base):
    """Database entity representing a workflow execution run."""

    __tablename__ = "relay_jobs"

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="PENDING")
    total_steps: Mapped[int] = mapped_column(nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    variables_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    steps: Mapped[list["StepRecord"]] = relationship(
        "StepRecord", back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary format for `IRepository` contract."""
        steps_dict = {s.step_name: s.to_dict() for s in self.steps}
        return {
            "job_id": self.job_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "total_steps": self.total_steps,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "variables": self.variables_json,
            "steps": steps_dict,
        }


class StepRecord(Base):
    """Database entity representing an atomic step execution outcome."""

    __tablename__ = "relay_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("relay_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(nullable=False, default=0.0)
    output_count: Mapped[int] = mapped_column(nullable=False, default=0)
    output_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    job: Mapped["JobRecord"] = relationship("JobRecord", back_populates="steps")

    def to_dict(self) -> dict[str, Any]:
        """Convert step record to dictionary."""
        return {
            "step_name": self.step_name,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "output_count": self.output_count,
            "output_ids": self.output_ids_json,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
