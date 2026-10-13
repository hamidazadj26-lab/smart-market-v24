from alembic import op
import sqlalchemy as sa
revision="0016_multi_market"; down_revision="0015_rbac"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column("markets",sa.Column("default_currency",sa.String(10),nullable=False,server_default="USD"))
    op.add_column("markets",sa.Column("languages",sa.JSON(),nullable=False,server_default="[]"))
    op.add_column("markets",sa.Column("incoterms",sa.JSON(),nullable=False,server_default="[]"))
    op.add_column("markets",sa.Column("transport_modes",sa.JSON(),nullable=False,server_default="[]"))
    op.add_column("markets",sa.Column("scoring_weights",sa.JSON(),nullable=False,server_default="{}"))
    op.add_column("markets",sa.Column("commercial_rules",sa.JSON(),nullable=False,server_default="{}"))
    op.add_column("opportunities",sa.Column("market_id",sa.Integer(),nullable=True))
    op.create_index("ix_opportunities_market_id","opportunities",["market_id"])
    with op.batch_alter_table("opportunities") as batch:
        batch.create_foreign_key("fk_opportunities_market_id","markets",["market_id"],["id"])
def downgrade():
    with op.batch_alter_table("opportunities") as batch:
        batch.drop_constraint("fk_opportunities_market_id",type_="foreignkey")
    op.drop_index("ix_opportunities_market_id",table_name="opportunities")
    op.drop_column("opportunities","market_id")
    for c in ["commercial_rules","scoring_weights","transport_modes","incoterms","languages","default_currency"]:
        op.drop_column("markets",c)
