"""SMART MARKET V20.2 explicit initial schema migration."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('admins',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(80), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('markets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_country', sa.String(100), nullable=False),
        sa.Column('target_country', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('normalized_name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(120)),
        sa.Column('sub_category', sa.String(120)),
        sa.Column('unit', sa.String(30)),
        sa.Column('aliases', sa.JSON(), nullable=False),
        sa.Column('specifications', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_type', sa.String(80), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('base_url', sa.String()),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('transport_providers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(250), nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('contact', sa.String(120)),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('verifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('reviewer', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('admin_id', sa.Integer(), sa.ForeignKey('admins.id')),
        sa.Column('action', sa.String(120), nullable=False),
        sa.Column('entity_type', sa.String(60)),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('customers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(250), nullable=False),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('city', sa.String(120)),
        sa.Column('address', sa.String()),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('activity_type', sa.String(200)),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id')),
        sa.Column('phone', sa.String(80)),
        sa.Column('website', sa.String()),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
        sa.Column('source_url', sa.String()),
        sa.Column('source_title', sa.String(300)),
        sa.Column('retrieved_at', sa.DateTime(timezone=True)),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('demands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('raw_text', sa.String()),
        sa.Column('quantity', sa.Float()),
        sa.Column('unit', sa.String(30)),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('city', sa.String(120)),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('urgency', sa.String(80)),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
        sa.Column('source_url', sa.String()),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('verification_notes', sa.String()),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('manufacturers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(250), nullable=False),
        sa.Column('company', sa.String(250)),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id')),
        sa.Column('country', sa.String(100), nullable=False),
        sa.Column('city', sa.String(120)),
        sa.Column('address', sa.String()),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('capacity_value', sa.Float()),
        sa.Column('capacity_unit', sa.String(30)),
        sa.Column('phone', sa.String(80)),
        sa.Column('website', sa.String()),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
        sa.Column('source_url', sa.String()),
        sa.Column('source_title', sa.String(300)),
        sa.Column('retrieved_at', sa.DateTime(timezone=True)),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('session_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('admin_id', sa.Integer(), sa.ForeignKey('admins.id'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('source_signals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
        sa.Column('raw_text', sa.String(), nullable=False),
        sa.Column('source_url', sa.String()),
        sa.Column('source_title', sa.String(300)),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('normalized_payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('transport_routes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('origin', sa.String(200), nullable=False),
        sa.Column('destination', sa.String(200), nullable=False),
        sa.Column('provider_id', sa.Integer(), sa.ForeignKey('transport_providers.id')),
        sa.Column('capacity', sa.Float()),
        sa.Column('capacity_unit', sa.String(30)),
        sa.Column('cost', sa.Float()),
        sa.Column('currency', sa.String(10)),
        sa.Column('eta_hours', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_table('opportunities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('manufacturer_id', sa.Integer(), sa.ForeignKey('manufacturers.id'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('demand_id', sa.Integer(), sa.ForeignKey('demands.id')),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('product_fit', sa.Float(), nullable=False),
        sa.Column('capacity_score', sa.Float(), nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=False),
        sa.Column('trust_score', sa.Float(), nullable=False),
        sa.Column('location_score', sa.Float(), nullable=False),
        sa.Column('distance_km', sa.Float()),
        sa.Column('route', sa.JSON(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('next_action', sa.String(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_admins_username', 'admins', ['username'])
    op.create_index('ix_markets_name', 'markets', ['name'])
    op.create_index('ix_markets_source_country', 'markets', ['source_country'])
    op.create_index('ix_markets_target_country', 'markets', ['target_country'])
    op.create_index('ix_products_category', 'products', ['category'])
    op.create_index('ix_products_name', 'products', ['name'])
    op.create_index('ix_products_normalized_name', 'products', ['normalized_name'])
    op.create_index('ix_sources_source_type', 'sources', ['source_type'])
    op.create_index('ix_transport_providers_name', 'transport_providers', ['name'])
    op.create_index('ix_verifications_status', 'verifications', ['status'])
    op.create_index('ix_verifications_entity_type', 'verifications', ['entity_type'])
    op.create_index('ix_verifications_entity_id', 'verifications', ['entity_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_admin_id', 'audit_logs', ['admin_id'])
    op.create_index('ix_customers_verification_status', 'customers', ['verification_status'])
    op.create_index('ix_customers_source_id', 'customers', ['source_id'])
    op.create_index('ix_customers_product_id', 'customers', ['product_id'])
    op.create_index('ix_customers_city', 'customers', ['city'])
    op.create_index('ix_customers_country', 'customers', ['country'])
    op.create_index('ix_customers_is_archived', 'customers', ['is_archived'])
    op.create_index('ix_customers_name', 'customers', ['name'])
    op.create_index('ix_demands_country', 'demands', ['country'])
    op.create_index('ix_demands_verification_status', 'demands', ['verification_status'])
    op.create_index('ix_demands_source_id', 'demands', ['source_id'])
    op.create_index('ix_demands_product_id', 'demands', ['product_id'])
    op.create_index('ix_demands_city', 'demands', ['city'])
    op.create_index('ix_demands_is_archived', 'demands', ['is_archived'])
    op.create_index('ix_manufacturers_verification_status', 'manufacturers', ['verification_status'])
    op.create_index('ix_manufacturers_product_id', 'manufacturers', ['product_id'])
    op.create_index('ix_manufacturers_is_archived', 'manufacturers', ['is_archived'])
    op.create_index('ix_manufacturers_name', 'manufacturers', ['name'])
    op.create_index('ix_manufacturers_city', 'manufacturers', ['city'])
    op.create_index('ix_manufacturers_country', 'manufacturers', ['country'])
    op.create_index('ix_manufacturers_source_id', 'manufacturers', ['source_id'])
    op.create_index('ix_session_tokens_admin_id', 'session_tokens', ['admin_id'])
    op.create_index('ix_session_tokens_expires_at', 'session_tokens', ['expires_at'])
    op.create_index('ix_session_tokens_token_hash', 'session_tokens', ['token_hash'])
    op.create_index('ix_source_signals_source_id', 'source_signals', ['source_id'])
    op.create_index('ix_source_signals_verification_status', 'source_signals', ['verification_status'])
    op.create_index('ix_transport_routes_origin', 'transport_routes', ['origin'])
    op.create_index('ix_transport_routes_destination', 'transport_routes', ['destination'])
    op.create_index('ix_opportunities_is_archived', 'opportunities', ['is_archived'])
    op.create_index('ix_opportunities_demand_id', 'opportunities', ['demand_id'])
    op.create_index('ix_opportunities_customer_id', 'opportunities', ['customer_id'])
    op.create_index('ix_opportunities_priority', 'opportunities', ['priority'])
    op.create_index('ix_opportunities_product_id', 'opportunities', ['product_id'])
    op.create_index('ix_opportunities_manufacturer_id', 'opportunities', ['manufacturer_id'])
    op.create_index('ix_opportunities_score', 'opportunities', ['score'])
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute("ALTER TABLE manufacturers ADD COLUMN IF NOT EXISTS geom geography(POINT,4326)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_manufacturers_geom ON manufacturers USING GIST (geom)")
        op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS geom geography(POINT,4326)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_customers_geom ON customers USING GIST (geom)")
        op.execute("ALTER TABLE demands ADD COLUMN IF NOT EXISTS geom geography(POINT,4326)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_demands_geom ON demands USING GIST (geom)")
        op.execute("CREATE OR REPLACE FUNCTION smart_market_sync_geom() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude),4326)::geography; ELSE NEW.geom = NULL; END IF; RETURN NEW; END $$")
        op.execute("DROP TRIGGER IF EXISTS trg_manufacturers_geom ON manufacturers")
        op.execute("CREATE TRIGGER trg_manufacturers_geom BEFORE INSERT OR UPDATE OF latitude, longitude ON manufacturers FOR EACH ROW EXECUTE FUNCTION smart_market_sync_geom()")
        op.execute("DROP TRIGGER IF EXISTS trg_customers_geom ON customers")
        op.execute("CREATE TRIGGER trg_customers_geom BEFORE INSERT OR UPDATE OF latitude, longitude ON customers FOR EACH ROW EXECUTE FUNCTION smart_market_sync_geom()")
        op.execute("DROP TRIGGER IF EXISTS trg_demands_geom ON demands")
        op.execute("CREATE TRIGGER trg_demands_geom BEFORE INSERT OR UPDATE OF latitude, longitude ON demands FOR EACH ROW EXECUTE FUNCTION smart_market_sync_geom()")

def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TRIGGER IF EXISTS trg_manufacturers_geom ON manufacturers")
        op.execute("DROP INDEX IF EXISTS ix_manufacturers_geom")
        op.execute("ALTER TABLE manufacturers DROP COLUMN IF EXISTS geom")
        op.execute("DROP TRIGGER IF EXISTS trg_customers_geom ON customers")
        op.execute("DROP INDEX IF EXISTS ix_customers_geom")
        op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS geom")
        op.execute("DROP TRIGGER IF EXISTS trg_demands_geom ON demands")
        op.execute("DROP INDEX IF EXISTS ix_demands_geom")
        op.execute("ALTER TABLE demands DROP COLUMN IF EXISTS geom")
    for table in reversed([t.name for t in Base.metadata.sorted_tables]):
        op.drop_table(table)