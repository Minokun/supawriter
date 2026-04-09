"""add hotspot tables

Revision ID: 4dfa64d23e69
Revises: 1169ab91989f
Create Date: 2026-02-28 01:19:21.926712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4dfa64d23e69'
down_revision: Union[str, Sequence[str], None] = '1169ab91989f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add hotspot tables."""
    # 创建平台配置表
    op.create_table(
        'hotspot_sources',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建热点主表
    op.create_table(
        'hotspot_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=200), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('rank_prev', sa.Integer(), nullable=True),
        sa.Column('rank_change', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hot_value', sa.Integer(), nullable=True),
        sa.Column('hot_value_prev', sa.Integer(), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(length=500), nullable=True),
        sa.Column('mobile_url', sa.String(length=1000), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source'], ['hotspot_sources.id'], ),
        sa.UniqueConstraint('title', 'source', name='uq_hotspot_title_source')
    )
    op.create_index('ix_hotspot_items_source', 'hotspot_items', ['source'])
    op.create_index('ix_hotspot_items_source_rank', 'hotspot_items', ['source', 'rank'])
    op.create_index('ix_hotspot_items_title', 'hotspot_items', ['title'])

    # 创建排名历史表
    op.create_table(
        'hotspot_rank_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hotspot_item_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('hot_value', sa.Integer(), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['hotspot_item_id'], ['hotspot_items.id'], ondelete='CASCADE')
    )
    op.create_index('ix_hotspot_rank_history_hotspot_item_id', 'hotspot_rank_history', ['hotspot_item_id'])
    op.create_index('ix_hotspot_rank_history_recorded_at', 'hotspot_rank_history', ['recorded_at'])
    op.create_index('ix_rank_history_item_time', 'hotspot_rank_history', ['hotspot_item_id', 'recorded_at'])


def downgrade() -> None:
    """Downgrade schema - remove hotspot tables."""
    op.drop_index('ix_rank_history_item_time', table_name='hotspot_rank_history')
    op.drop_index('ix_hotspot_rank_history_recorded_at', table_name='hotspot_rank_history')
    op.drop_index('ix_hotspot_rank_history_hotspot_item_id', table_name='hotspot_rank_history')
    op.drop_table('hotspot_rank_history')

    op.drop_index('ix_hotspot_items_title', table_name='hotspot_items')
    op.drop_index('ix_hotspot_items_source_rank', table_name='hotspot_items')
    op.drop_index('ix_hotspot_items_source', table_name='hotspot_items')
    op.drop_table('hotspot_items')

    op.drop_table('hotspot_sources')
