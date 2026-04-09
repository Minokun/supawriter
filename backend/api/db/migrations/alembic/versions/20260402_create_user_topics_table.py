"""create user_topics table if missing

Revision ID: 20260402_user_topics_fix
Revises: 20260401_allow_superuser_membership_tier
Create Date: 2026-04-02 16:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_user_topics_fix"
down_revision: Union[str, Sequence[str], None] = "20260401_allow_superuser_membership_tier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "user_topics"
USER_ID_INDEX = "ix_user_topics_user_id"
ID_INDEX = "ix_user_topics_id"
UNIQUE_CONSTRAINT = "user_topics_user_id_topic_name_key"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if TABLE_NAME not in table_names:
        op.create_table(
            "user_topics",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("topic_name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        table_names.add(TABLE_NAME)

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if ID_INDEX not in indexes:
        op.create_index(ID_INDEX, TABLE_NAME, ["id"], unique=False)
    if USER_ID_INDEX not in indexes:
        op.create_index(USER_ID_INDEX, TABLE_NAME, ["user_id"], unique=False)

    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints(TABLE_NAME)}
    if UNIQUE_CONSTRAINT not in unique_constraints:
        op.create_unique_constraint(UNIQUE_CONSTRAINT, TABLE_NAME, ["user_id", "topic_name"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if TABLE_NAME in table_names:
        op.drop_table(TABLE_NAME)
