"""add empresa and summary_json to plans

Revision ID: a1b2c3d4e5f6
Revises: 048b50b598ce
Create Date: 2026-03-10 05:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '048b50b598ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('empresa', sa.String(length=200), nullable=False, server_default=''))
    op.add_column('plans', sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'summary_json')
    op.drop_column('plans', 'empresa')
