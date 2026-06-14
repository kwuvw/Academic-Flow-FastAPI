"""add_file_original_name_to_tasks

Revision ID: e7f2a1b3c4d5
Revises: d5a3e1e2cd26
Create Date: 2026-06-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from src.tasks.models import Task


# revision identifiers, used by Alembic.
revision: str = 'e7f2a1b3c4d5'
down_revision: Union[str, None] = 'd5a3e1e2cd26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('file_original_name', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'file_original_name')
