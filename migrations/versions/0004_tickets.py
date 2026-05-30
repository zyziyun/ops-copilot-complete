"""tickets table (C3 write tool target)

Revision ID: 0004_tickets
Revises: 0003_tsvector_gin
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_tickets"
down_revision: Union[str, None] = "0003_tsvector_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.Text),
        sa.Column("severity", sa.String(32)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("tickets")
