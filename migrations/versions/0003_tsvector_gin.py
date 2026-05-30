"""generated content_tsv column + GIN index

Revision ID: 0003_tsvector_gin
Revises: 0002_source_system
Create Date: 2026-01-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_tsvector_gin"
down_revision: Union[str, None] = "0002_source_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
        """
    )
    op.execute("CREATE INDEX chunks_tsv_gin ON chunks USING gin (content_tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chunks_tsv_gin")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content_tsv")
