"""add source_system column

Revision ID: 0002_source_system
Revises: 0001_chunks
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_source_system"
down_revision: Union[str, None] = "0001_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "source_system",
            sa.String(32),
            server_default="unknown",
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chunks", "source_system")
