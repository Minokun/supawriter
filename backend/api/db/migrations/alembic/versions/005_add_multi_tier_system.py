"""Add multi-tier membership system

Revision ID: 005_add_multi_tier_system
Revises: 15596338944b
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '005_add_multi_tier_system'
down_revision: Union[str, Sequence[str], None] = '15596338944b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库架构"""

    # 1. 添加 membership_tier 列到 users 表
    op.add_column(
        'users',
        sa.Column(
            'membership_tier',
            sa.String(20),
            server_default='free',
            nullable=False
        )
    )

    # 添加约束确保 tier 值合法
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT check_membership_tier
        CHECK (membership_tier IN ('free', 'pro', 'ultra'))
    """)

    # 2. 创建全局 LLM 提供商表
    # models 字段结构: [{"name": "deepseek-chat", "min_tier": "free"}, {"name": "gpt-4", "min_tier": "ultra"}]
    op.create_table(
        'global_llm_providers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.String(50), nullable=False),
        sa.Column('provider_name', sa.String(100), nullable=False),
        sa.Column('base_url', sa.Text(), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('models', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_id')
    )
    op.create_index('ix_global_llm_providers_id', 'global_llm_providers', ['id'])

    # 4. 创建等级默认模型和配额表
    op.create_table(
        'tier_default_models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('default_chat_model', sa.String(200), nullable=True),
        sa.Column('default_writer_model', sa.String(200), nullable=True),
        sa.Column('article_limit_per_month', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tier')
    )
    op.create_index('ix_tier_default_models_id', 'tier_default_models', ['id'])

    # 添加约束确保 tier 值合法
    op.execute("""
        ALTER TABLE tier_default_models
        ADD CONSTRAINT check_tier_default_tier
        CHECK (tier IN ('free', 'pro', 'ultra'))
    """)

    # 5. 插入初始等级数据
    op.execute("""
        INSERT INTO tier_default_models (tier, default_chat_model, default_writer_model, article_limit_per_month)
        VALUES
            ('free', 'deepseek:deepseek-chat', 'deepseek:deepseek-chat', 5),
            ('pro', 'deepseek:deepseek-chat', 'deepseek:deepseek-chat', 15),
            ('ultra', 'deepseek:deepseek-chat', 'deepseek:deepseek-chat', 30)
        ON CONFLICT (tier) DO NOTHING
    """)


def downgrade() -> None:
    """回滚数据库架构"""

    # 删除表（按依赖顺序）
    op.drop_table('tier_default_models')
    op.drop_table('global_llm_providers')

    # 删除 users 表的列和约束
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_membership_tier")
    op.drop_column('users', 'membership_tier')
