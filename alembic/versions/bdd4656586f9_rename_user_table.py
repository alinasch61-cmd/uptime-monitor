"""rename user table

Revision ID: bdd4656586f9
Revises: 3deaefde6724
Create Date: 2026-09-16 14:57:39.295130

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdd4656586f9"
down_revision: str | Sequence[str] | None = "3deaefde6724"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("user", "monitor_user")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("monitor_user", "user")
