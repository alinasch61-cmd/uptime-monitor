"""add next_check_at trigger

Revision ID: de40c846f8c7
Revises: d9cd9b08da7d
Create Date: 2026-09-21 15:43:36.640843

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de40c846f8c7"
down_revision: str | Sequence[str] | None = "d9cd9b08da7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE FUNCTION update_next_check_at()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.is_paused = TRUE AND NEW.is_paused = FALSE THEN
                NEW.next_check_at = NOW();
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER update_next_check_at_trigger
        BEFORE UPDATE ON endpoint
        FOR EACH ROW
        EXECUTE FUNCTION update_next_check_at();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""DROP TRIGGER update_next_check_at_trigger ON endpoint;""")
    op.execute("""DROP FUNCTION update_next_check_at;""")
