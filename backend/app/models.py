import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    vessel_type: Mapped[str] = mapped_column(String(80), default="Handymax bulk (OPEN-01)")
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="project")
    jobs: Mapped[list["OptimizationJob"]] = relationship(back_populates="project")
    reviews: Mapped[list["Review"]] = relationship(back_populates="project")


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("optimization_jobs.id"), nullable=True)
    length_pp: Mapped[float] = mapped_column(Float)
    beam: Mapped[float] = mapped_column(Float)
    draft: Mapped[float] = mapped_column(Float)
    block_coefficient: Mapped[float] = mapped_column(Float)
    prismatic_coefficient: Mapped[float] = mapped_column(Float)
    volume_m3: Mapped[float] = mapped_column(Float)
    displacement_tonnes: Mapped[float] = mapped_column(Float)
    demo_score: Mapped[float] = mapped_column(Float)
    volume_gap: Mapped[float] = mapped_column(Float)
    pareto: Mapped[bool] = mapped_column(Boolean, default=False)
    feasible: Mapped[bool] = mapped_column(Boolean, default=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(40))
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adopted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[Project] = relationship(back_populates="candidates")


class OptimizationJob(Base):
    __tablename__ = "optimization_jobs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    model_version: Mapped[str] = mapped_column(String(40))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project: Mapped[Project] = relationship(back_populates="jobs")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"))
    decision: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(80), default="designer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[Project] = relationship(back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
