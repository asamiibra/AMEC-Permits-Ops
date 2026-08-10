"""Persistent Dashboard master-content readiness inputs."""

from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class DashboardInputItem(Base):
    __tablename__ = "dashboard_input_items"
    __table_args__ = (UniqueConstraint("context_key", "input_key", name="uq_dashboard_input_context_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    context_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True, default="DASHBOARD_MASTER_CONTENT")
    input_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    why_needed: Mapped[str] = mapped_column(Text, nullable=False)
    requested_input: Mapped[str] = mapped_column(Text, nullable=False)
    current_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_CONFIRMATION", index=True)
    blocking_level: Mapped[str] = mapped_column(String(40), nullable=False, default="BUSINESS")
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False, default="OWNER")
    linked_route: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(120))
    confirmed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[Any] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
