"""Add alert keywords, records and user stats tables

Revision ID: a5baafcd26ed
Revises: 005_add_multi_tier_system
Create Date: 2026-02-20 10:40:24.390884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a5baafcd26ed'
down_revision: Union[str, Sequence[str], None] = '005_add_multi_tier_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create alert_keywords table
    op.create_table('alert_keywords',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_keywords_id'), 'alert_keywords', ['id'], unique=False)
    op.create_index(op.f('ix_alert_keywords_user_id'), 'alert_keywords', ['user_id'], unique=False)

    # Create user_stats table
    op.create_table('user_stats',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_articles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_words', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_articles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quota_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_score', sa.Float(), nullable=True),
        sa.Column('score_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('platform_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hotspot_matches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('keyword_hit_rate', sa.Float(), nullable=True),
        sa.Column('model_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create alert_records table
    op.create_table('alert_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.UUID(), nullable=False),
        sa.Column('hotspot_title', sa.String(length=500), nullable=False),
        sa.Column('hotspot_source', sa.String(length=50), nullable=False),
        sa.Column('hotspot_url', sa.String(length=1000), nullable=True),
        sa.Column('hotspot_id', sa.String(length=100), nullable=True),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['keyword_id'], ['alert_keywords.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_records_id'), 'alert_records', ['id'], unique=False)
    op.create_index(op.f('ix_alert_records_keyword_id'), 'alert_records', ['keyword_id'], unique=False)
    op.create_index(op.f('ix_alert_records_user_id'), 'alert_records', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_alert_records_user_id'), table_name='alert_records')
    op.drop_index(op.f('ix_alert_records_keyword_id'), table_name='alert_records')
    op.drop_index(op.f('ix_alert_records_id'), table_name='alert_records')
    op.drop_table('alert_records')
    op.drop_table('user_stats')
    op.drop_index(op.f('ix_alert_keywords_user_id'), table_name='alert_keywords')
    op.drop_index(op.f('ix_alert_keywords_id'), table_name='alert_keywords')
    op.drop_table('alert_keywords')
