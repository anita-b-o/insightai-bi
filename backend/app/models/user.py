from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint, desc, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def _dashboard_share_links_order_by():
    from app.models.dashboard_share_link import DashboardShareLink

    return desc(DashboardShareLink.created_at)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    query_history: Mapped[list["QueryHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(QueryHistory.created_at)",
    )
    insight_runs: Mapped[list["DatasetInsightRun"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(DatasetInsightRun.generated_at)",
    )
    dashboards: Mapped[list["Dashboard"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Dashboard.updated_at)",
    )
    dashboard_share_links: Mapped[list["DashboardShareLink"]] = relationship(
        back_populates="created_by",
        cascade="all, delete-orphan",
        order_by=_dashboard_share_links_order_by,
    )
