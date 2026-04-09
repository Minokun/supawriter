"""allow superuser membership tier"""

from alembic import op

revision = "20260401_allow_superuser_membership_tier"
down_revision = "4dfa64d23e69"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    op.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra', 'superuser')) NOT VALID
        """
    )
    op.execute("ALTER TABLE users VALIDATE CONSTRAINT check_membership_tier")


def downgrade() -> None:
    op.execute("UPDATE users SET membership_tier = 'ultra' WHERE membership_tier = 'superuser'")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    op.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra')) NOT VALID
        """
    )
    op.execute("ALTER TABLE users VALIDATE CONSTRAINT check_membership_tier")
