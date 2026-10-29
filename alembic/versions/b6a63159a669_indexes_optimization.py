"""indexes optimization

Revision ID: b6a63159a669
Revises: 636705cbc612
Create Date: 2026-10-28 15:06:56.092378

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6a63159a669"
down_revision: str | Sequence[str] | None = "636705cbc612"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(index_name="ix_endpoint_id_checked_at")
    op.create_index(
        "ix_check_result_id_checked_at_endpoint_id",
        "check_result",
        ["endpoint_id", "checked_at", "id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_check_result_id_checked_at_endpoint_id", table_name="check_result"
    )
    op.create_index(
        "ix_endpoint_id_checked_at",
        "check_result",
        ["endpoint_id", "checked_at"],
        unique=False,
    )
    # ### end Alembic commands ###
