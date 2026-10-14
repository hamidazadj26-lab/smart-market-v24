"""Enforce natural-key uniqueness and entity-link integrity."""
from alembic import op
import sqlalchemy as sa

revision = "0042_entity_identity_integrity"
down_revision = "0041_align_transport_provider_and_freshness_schema"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    duplicate_identity = connection.execute(sa.text("""
        SELECT 1
        FROM entity_identities
        GROUP BY entity_type, entity_id, identity_type, normalized_value
        HAVING COUNT(*) > 1
        LIMIT 1
    """)).first()
    if duplicate_identity:
        raise RuntimeError(
            "Cannot add entity identity uniqueness: duplicate natural keys exist "
            "in entity_identities. Review/merge duplicates before retrying migration."
        )

    invalid_confidence = connection.execute(sa.text("""
        SELECT 1 FROM entity_identities
        WHERE confidence < 0 OR confidence > 1
        LIMIT 1
    """)).first()
    if invalid_confidence:
        raise RuntimeError(
            "Cannot enforce entity identity confidence range: values outside [0, 1] exist."
        )

    self_link = connection.execute(sa.text("""
        SELECT 1 FROM entity_links
        WHERE left_type = right_type AND left_id = right_id
        LIMIT 1
    """)).first()
    if self_link:
        raise RuntimeError(
            "Cannot enforce entity link integrity: self-links exist in entity_links."
        )

    op.create_index(
        "ux_entity_identities_natural_key",
        "entity_identities",
        ["entity_type", "entity_id", "identity_type", "normalized_value"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_entity_identities_confidence_range",
        "entity_identities",
        "confidence >= 0 AND confidence <= 1",
    )
    op.create_check_constraint(
        "ck_entity_links_not_self",
        "entity_links",
        "NOT (left_type = right_type AND left_id = right_id)",
    )


def downgrade():
    op.drop_constraint("ck_entity_links_not_self", "entity_links", type_="check")
    op.drop_constraint(
        "ck_entity_identities_confidence_range",
        "entity_identities",
        type_="check",
    )
    op.drop_index("ux_entity_identities_natural_key", table_name="entity_identities")
