from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    toxicity_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    toxic_messages: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    strikes: Mapped[int] = mapped_column(Integer, default=0)
    timeout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user", lazy="select")
    moderation_actions: Mapped[list["ModerationAction"]] = relationship(
        "ModerationAction", back_populates="target_user", lazy="select"
    )
