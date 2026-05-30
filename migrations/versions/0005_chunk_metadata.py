"""structured JSONB metadata + modality column on chunks

Revision ID: 0005_chunk_metadata
Revises: 0004_tickets
Create Date: 2026-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005_chunk_metadata"
down_revision: Union[str, None] = "0004_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # structured fields co-located with the vector, queryable in the same SQL
    op.add_column(
        "chunks",
        sa.Column("doc_metadata", JSONB, server_default="{}", nullable=False),
    )
    # modality: text | table | image (drives how the chunk was produced)
    op.add_column(
        "chunks",
        sa.Column(
            "modality", sa.String(16), server_default="text", index=True
        ),
    )
    # GIN index so `doc_metadata @> '{"severity":"high"}'` containment is fast
    op.execute(
        "CREATE INDEX chunks_meta_gin ON chunks USING gin (doc_metadata)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chunks_meta_gin")
    op.drop_column("chunks", "modality")
    op.drop_column("chunks", "doc_metadata")
