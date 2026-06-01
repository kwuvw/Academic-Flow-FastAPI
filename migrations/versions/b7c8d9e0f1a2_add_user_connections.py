"""add user_connections table

Revision ID: b7c8d9e0f1a2
Revises: a383f48cfafd
Create Date: 2026-05-31 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a383f48cfafd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "teacher_id", name="uq_student_teacher"),
    )
    op.create_index(
        op.f("ix_user_connections_student_id"),
        "user_connections",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_connections_teacher_id"),
        "user_connections",
        ["teacher_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_connections_teacher_id"), table_name="user_connections")
    op.drop_index(op.f("ix_user_connections_student_id"), table_name="user_connections")
    op.drop_table("user_connections")
