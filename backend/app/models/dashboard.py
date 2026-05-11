from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, desc, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def _share_links_order_by():
    from app.models.dashboard_share_link import DashboardShareLink

    return desc(DashboardShareLink.created_at)


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    auto_refresh_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    refresh_in_progress: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    refresh_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refresh_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_successful_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(20), nullable=False, default="never_refreshed", server_default="never_refreshed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="dashboards")
    dataset: Mapped["Dataset"] = relationship()
    widgets: Mapped[list["DashboardWidget"]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardWidget.created_at",
    )
    share_links: Mapped[list["DashboardShareLink"]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by=_share_links_order_by,
    )
