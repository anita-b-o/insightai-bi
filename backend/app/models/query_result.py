from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class QueryResult(Base):
    __tablename__ = "query_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("query_history.id", ondelete="CASCADE"), unique=True, index=True)
    result_json: Mapped[dict] = mapped_column(JSONB)
    visualization_suggestion: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    visualization_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    query: Mapped["QueryHistory"] = relationship(back_populates="result")
