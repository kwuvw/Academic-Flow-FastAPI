"""add department column to users

Revision ID: d4e5f6a7b8c9
Revises: 32f94c42183c
Create Date: 2026-06-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "32f94c42183c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("department", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "department")
