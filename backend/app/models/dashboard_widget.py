from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    dashboard_id: Mapped[int] = mapped_column(ForeignKey("dashboards.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_type: Mapped[str] = mapped_column(String(20), default="snapshot", server_default="snapshot")
    execution_status: Mapped[str] = mapped_column(String(20), default="never_run", server_default="never_run")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chart_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    query_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    data_json: Mapped[list[dict[str, object]] | dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    layout: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    snapshot_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    snapshot_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dashboard: Mapped["Dashboard"] = relationship(back_populates="widgets")
