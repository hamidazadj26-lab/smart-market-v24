"""Align transport-provider strategy fields and freshness invariants."""
from alembic import op
import sqlalchemy as sa

revision = "0041_align_transport_provider_and_freshness_schema"
down_revision = "0040_commercial_offer_fx_provenance"
branch_labels = None
depends_on = None


def upgrade():
    for name, typ, default in (
        ("default_currency", sa.String(10), "USD"),
        ("languages", sa.JSON(), sa.text("'[]'")),
        ("incoterms", sa.JSON(), sa.text("'[]'")),
        ("transport_modes", sa.JSON(), sa.text("'[]'")),
        ("scoring_weights", sa.JSON(), sa.text("'{}'")),
        ("commercial_rules", sa.JSON(), sa.text("'{}'")),
    ):
        op.add_column(
            "transport_providers",
            sa.Column(name, typ, nullable=False, server_default=default),
        )

    # Backfill old rows before matching the ORM's non-null freshness status.
    for table in ("sources", "source_signals", "demands"):
        op.execute(
            sa.text(f"UPDATE {table} SET freshness_status = 'Unknown' "
                    "WHERE freshness_status IS NULL")
        )
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "freshness_status",
                existing_type=sa.String(30),
                nullable=False,
                server_default="Unknown",
            )

    # Align identity graph integrity and JSON payload nullability.
    op.execute(sa.text(
        "UPDATE entity_identities SET evidence = '{}' WHERE evidence IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE entity_links SET reasons = '[]' WHERE reasons IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE entity_links SET evidence = '{}' WHERE evidence IS NULL"
    ))
    with op.batch_alter_table("entity_identities") as batch:
        batch.alter_column(
            "evidence", existing_type=sa.JSON(), nullable=False,
            server_default=sa.text("'{}'"),
        )
        batch.create_foreign_key(
            "fk_entity_identities_source_id", "sources", ["source_id"], ["id"]
        )
    with op.batch_alter_table("entity_links") as batch:
        batch.alter_column(
            "reasons", existing_type=sa.JSON(), nullable=False,
            server_default=sa.text("'[]'"),
        )
        batch.alter_column(
            "evidence", existing_type=sa.JSON(), nullable=False,
            server_default=sa.text("'{}'"),
        )

    # The freshness model marks these fields indexed. Earlier migrations added
    # the columns but omitted their indexes.
    freshness_indexes = {
        "sources": (
            "freshness_status", "freshness_score", "observed_at",
            "published_at", "updated_at_source", "expires_at", "last_verified_at",
        ),
        "source_signals": (
            "freshness_status", "freshness_score", "observed_at",
            "updated_at_source", "expires_at", "last_verified_at",
        ),
        "demands": (
            "freshness_status", "freshness_score", "observed_at",
            "updated_at_source", "expires_at", "last_verified_at",
        ),
    }
    for table, columns in freshness_indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table, columns in (
        ("demands", (
            "freshness_status", "freshness_score", "observed_at",
            "updated_at_source", "expires_at", "last_verified_at",
        )),
        ("source_signals", (
            "freshness_status", "freshness_score", "observed_at",
            "updated_at_source", "expires_at", "last_verified_at",
        )),
        ("sources", (
            "freshness_status", "freshness_score", "observed_at",
            "published_at", "updated_at_source", "expires_at", "last_verified_at",
        )),
    ):
        for column in columns:
            op.drop_index(f"ix_{table}_{column}", table_name=table)

    with op.batch_alter_table("entity_links") as batch:
        batch.alter_column("evidence", existing_type=sa.JSON(), nullable=True, server_default=None)
        batch.alter_column("reasons", existing_type=sa.JSON(), nullable=True, server_default=None)
    with op.batch_alter_table("entity_identities") as batch:
        batch.drop_constraint("fk_entity_identities_source_id", type_="foreignkey")
        batch.alter_column("evidence", existing_type=sa.JSON(), nullable=True, server_default=None)

    for table in ("demands", "source_signals", "sources"):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "freshness_status",
                existing_type=sa.String(30),
                nullable=True,
                server_default=None,
            )

    for name in (
        "commercial_rules", "scoring_weights", "transport_modes",
        "incoterms", "languages", "default_currency",
    ):
        op.drop_column("transport_providers", name)
