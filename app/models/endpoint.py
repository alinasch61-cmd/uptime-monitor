from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.check_result import CheckResult


class Endpoint(Base):
    __tablename__ = "endpoint"
    __table_args__ = (
        CheckConstraint(
            "expected_status_code >= 100 AND expected_status_code <= 599",
            name="ck_endpoint_expected_status_code_range",
        ),
        CheckConstraint(
            "check_frequency_seconds >= 120",
            name="ck_endpoint_expected_frequency_seconds",
        ),
        UniqueConstraint(
            "user_id",
            "url",
            "expected_status_code",
            name="uq_endpoint_user_url_status",
        ),
        Index(
            "ix_endpoint_next_check_at_active",
            "next_check_at",
            postgresql_where=text("is_paused = false")
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2000))
    expected_status_code: Mapped[int]
    check_frequency_seconds: Mapped[int]
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="endpoints")
    check_results: Mapped[list["CheckResult"]] = relationship(
        back_populates="endpoint", 
        cascade="all, delete", 
        passive_deletes=True
    )
    