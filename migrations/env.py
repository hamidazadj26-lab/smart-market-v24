from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import String, Text, create_engine, inspect, pool
from sqlalchemy.schema import Index

from app.database import Base
from app.models import *
from app.config import get_settings

config = context.config


def _database_url():
    """Use the explicit runtime DATABASE_URL before the application fallback."""
    return os.environ.get("DATABASE_URL") or get_settings().database_url


# ConfigParser treats percent signs as interpolation markers; escape them when
# storing a URL in Alembic config, while passing the original URL to offline mode.
config.set_main_option("sqlalchemy.url", _database_url().replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_reflected_index_signatures = set()


def _compare_type(context_, inspected_column, metadata_column, inspected_type, metadata_type):
    """Avoid churn for equivalent unbounded PostgreSQL VARCHAR/TEXT declarations."""
    string_types = (String, Text)
    if isinstance(inspected_type, string_types) and isinstance(metadata_type, string_types):
        if getattr(inspected_type, "length", None) is None and getattr(metadata_type, "length", None) is None:
            return False
    return None


def _non_default_options(options):
    """Normalize dialect-specific index options while retaining meaningful differences."""
    normalized = []
    try:
        items = options.items()
    except AttributeError:
        return ()

    for dialect, dialect_options in items:
        try:
            option_items = dialect_options.items()
        except AttributeError:
            option_items = ()
        for key, value in option_items:
            if value is None or value is False or value == {} or value == [] or value == ():
                continue
            # PostgreSQL's default index method is btree; don't treat its reflection
            # spelling as a semantic difference from SQLAlchemy's implicit default.
            if dialect == "postgresql" and key == "using" and value == "btree":
                continue
            normalized.append((str(dialect), str(key), str(value)))
    return tuple(sorted(normalized))


def _index_signature(index, table_name=None):
    """Return index shape without its cosmetic name; preserve order and uniqueness."""
    if isinstance(index, dict):
        columns = tuple(index.get("column_names") or ())
        unique = bool(index.get("unique", False))
        options = index.get("dialect_options") or {}
        # Some SQLAlchemy dialects expose index options at the top level.
        flattened = dict(options)
        for key, value in index.items():
            if key.startswith(("postgresql_", "sqlite_", "mysql_")):
                flattened[key] = value
        normalized_options = tuple(sorted(
            (str(key), str(value)) for key, value in flattened.items()
            if value is not None and value is not False and value not in ({}, [], ())
            and not (key == "postgresql_using" and value == "btree")
        ))
        table = table_name or index.get("table_name")
    else:
        columns = tuple(getattr(column, "name", None) for column in getattr(index, "columns", ()))
        unique = bool(getattr(index, "unique", False))
        normalized_options = _non_default_options(getattr(index, "dialect_options", {}))
        table = table_name or getattr(getattr(index, "table", None), "name", None)

    if not table or not columns or any(column is None for column in columns):
        return None
    return table, columns, unique, normalized_options


def _load_reflected_index_signatures(connection):
    """Cache live index shapes so equivalent legacy names can be matched both ways."""
    signatures = set()
    inspector = inspect(connection)
    for table_name in inspector.get_table_names():
        try:
            indexes = inspector.get_indexes(table_name)
        except Exception:
            # Keep the schema audit conservative if a table's indexes cannot be inspected.
            continue
        for index in indexes:
            signature = _index_signature(index, table_name)
            if signature is not None:
                signatures.add(signature)
    return signatures


def _include_object(object_, name, type_, reflected, compare_to):
    """Ignore extension-owned objects and cosmetic index-name drift, not shape changes."""
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

        signature = _index_signature(object_)
        if signature is not None:
            # Alembic's compare_to is commonly None when the index names differ.
            # Match exact schema shapes against the opposite side explicitly.
            if reflected:
                table = signature[0]
                metadata_table = target_metadata.tables.get(table)
                if metadata_table is not None:
                    for metadata_index in metadata_table.indexes:
                        if _index_signature(metadata_index, table) == signature:
                            return False
            elif signature in _reflected_index_signatures:
                return False
    return True


def run_migrations_offline():
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=_compare_type,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    global _reflected_index_signatures
    # Build the engine directly from the same explicit URL used by the
    # verifier. This avoids any stale or overridden sqlalchemy.url in Alembic
    # ConfigParser sections and guarantees the migration target is DATABASE_URL.
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        database_identity = connection.execute(
            __import__("sqlalchemy").text(
                "SELECT current_database(), current_schema(), current_setting('search_path')"
            )
        ).one()
        print(f"Alembic migration database identity: {database_identity}")
        _reflected_index_signatures = _load_reflected_index_signatures(connection)
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
