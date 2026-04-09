"""Update tier_default_models quotas to match PricingService

Revision ID: 20260406_update_tier_quotas
Revises: 20260402_create_user_topics_table
Create Date: 2026-04-06

pro: 15 -> 20, ultra: 30 -> 60
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260406_update_tier_quotas"
down_revision: Union[str, Sequence[str], None] = "20260402_create_user_topics_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE tier_default_models
        SET article_limit_per_month = 20, updated_at = NOW()
        WHERE tier = 'pro'
    """)
    op.execute("""
        UPDATE tier_default_models
        SET article_limit_per_month = 60, updated_at = NOW()
        WHERE tier = 'ultra'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE tier_default_models
        SET article_limit_per_month = 15, updated_at = NOW()
        WHERE tier = 'pro'
    """)
    op.execute("""
        UPDATE tier_default_models
        SET article_limit_per_month = 30, updated_at = NOW()
        WHERE tier = 'ultra'
    """)
