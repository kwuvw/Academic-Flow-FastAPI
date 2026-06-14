from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_name: Mapped[str] = mapped_column(String(length=50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(length=300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_paths: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_original_name: Mapped[str | None] = mapped_column(String(length=500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    teacher: Mapped["User"] = relationship("User", foreign_keys=[teacher_id], lazy="selectin")
