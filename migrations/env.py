from logging.config import fileConfig

from alembic import context
from sqlalchemy import String, Text, engine_from_config, pool

from app.database import Base
from app.models import *
from app.config import get_settings

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _compare_type(context_, inspected_column, metadata_column, inspected_type, metadata_type):
    """Avoid churn for equivalent unbounded PostgreSQL VARCHAR/TEXT declarations."""
    string_types = (String, Text)
    if isinstance(inspected_type, string_types) and isinstance(metadata_type, string_types):
        if getattr(inspected_type, "length", None) is None and getattr(metadata_type, "length", None) is None:
            return False
    return None


def _index_signature(index):
    """Return the schema-relevant shape of an index, excluding its name."""
    columns = tuple(getattr(column, "name", None) for column in getattr(index, "columns", ()))
    if not columns or any(column is None for column in columns):
        return None
    dialect_options = repr(getattr(index, "dialect_options", {}))
    return columns, bool(getattr(index, "unique", False)), dialect_options


def _include_object(object_, name, type_, reflected, compare_to):
    """Ignore extension-owned objects and name-only index drift, not shape changes."""
    if type_ == "table" and name == "spatial_ref_sys" and reflected:
        return False

    # Legacy spatial columns/indexes are created by migrations for spatial queries,
    # but are intentionally not mapped in the ORM. Alembic must not propose dropping them.
    if reflected and type_ == "column" and name == "geom":
        return False
    if type_ == "index":
        columns = getattr(object_, "columns", ())
        if reflected and (
            name.endswith("_geom")
            or any(getattr(column, "name", None) == "geom" for column in columns)
        ):
            return False

        # Several historical migrations use concise index names while SQLAlchemy
        # generates table/column-based names. If both indexes have identical ordered
        # columns, uniqueness, and dialect options, their names are cosmetic. Ignore
        # only this exact equivalence; composite-vs-single-column and unique-vs-
        # non-unique differences must remain visible to the blocking schema gate.
        if compare_to is not None and type(compare_to).__name__ == "Index":
            if _index_signature(object_) == _index_signature(compare_to):
                return False
    return True


def run_migrations_offline():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=_compare_type,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=_compare_type,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
