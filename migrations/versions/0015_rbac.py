from alembic import op
import sqlalchemy as sa
revision="0015_rbac"; down_revision="0014_watchtower_alerts"; branch_labels=None; depends_on=None
def upgrade():
 op.add_column("admins",sa.Column("role",sa.String(40),nullable=False,server_default="Admin")); op.create_index("ix_admins_role","admins",["role"])
def downgrade():
 op.drop_index("ix_admins_role",table_name="admins"); op.drop_column("admins","role")
