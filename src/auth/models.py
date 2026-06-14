import enum

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"


class ConnectionStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=20),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    first_name: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(length=100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column("patronymic", String(length=100), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(length=50), nullable=True)
    course_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department: Mapped[str | None] = mapped_column(String(length=200), nullable=True)


class UserConnection(Base):
    __tablename__ = "user_connections"
    __table_args__ = (
        UniqueConstraint("student_id", "teacher_id", name="uq_student_teacher"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="connection_status", native_enum=False, length=20),
        nullable=False,
    )
