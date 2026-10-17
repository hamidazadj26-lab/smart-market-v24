"""V22.0 opportunity operating system stage fields

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_opportunity_operating_system"
down_revision = "0010_market_price_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL enforces the VARCHAR(32) limit of Alembic's version table,
    # while SQLite ignores VARCHAR length declarations and does not support
    # ALTER COLUMN TYPE. Widen the column only on PostgreSQL.
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=False,
        )

    op.add_column("opportunities", sa.Column("opportunity_stage", sa.String(length=40), nullable=False, server_default="Discovered"))
    op.add_column("opportunities", sa.Column("stage_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opportunities", sa.Column("stage_owner_id", sa.Integer(), nullable=True))
    op.add_column("opportunities", sa.Column("stage_reason", sa.Text(), nullable=True))
    op.add_column("opportunities", sa.Column("lost_reason", sa.Text(), nullable=True))
    op.add_column("opportunities", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opportunities", sa.Column("stage_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    with op.batch_alter_table("opportunities") as batch:
        batch.create_foreign_key("fk_opportunities_stage_owner", "admins", ["stage_owner_id"], ["id"])
    op.create_index("ix_opportunities_opportunity_stage", "opportunities", ["opportunity_stage"])
    op.create_index("ix_opportunities_stage_due_at", "opportunities", ["stage_due_at"])
    op.create_index("ix_opportunities_stage_owner_id", "opportunities", ["stage_owner_id"])
    op.create_index("ix_opportunities_stage_updated_at", "opportunities", ["stage_updated_at"])


def downgrade():
    op.drop_index("ix_opportunities_stage_updated_at", table_name="opportunities")
    op.drop_index("ix_opportunities_stage_owner_id", table_name="opportunities")
    op.drop_index("ix_opportunities_stage_due_at", table_name="opportunities")
    op.drop_index("ix_opportunities_opportunity_stage", table_name="opportunities")
    with op.batch_alter_table("opportunities") as batch:
        batch.drop_constraint("fk_opportunities_stage_owner", type_="foreignkey")
    for col in ["stage_updated_at", "closed_at", "lost_reason", "stage_reason", "stage_owner_id", "stage_due_at", "opportunity_stage"]:
        op.drop_column("opportunities", col)
