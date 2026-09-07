from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.schemas.check_result import Status

if TYPE_CHECKING:
    from app.models.endpoint import Endpoint


class CheckResult(Base):
    __tablename__ = "check_result"
    __table_args__ = (
        CheckConstraint(
            "status_code >= 100 AND status_code <= 599",
            name="ck_check_point_status_code_range",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoint.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    latency_ms: Mapped[int] = mapped_column(nullable=True)
    status_code: Mapped[int] = mapped_column(nullable=True)
    result_status: Mapped[Status] = mapped_column(Enum(Status))
    error_type: Mapped[str] = mapped_column(String(255))
    endpoint: Mapped["Endpoint"] = relationship(back_populates="check_results")