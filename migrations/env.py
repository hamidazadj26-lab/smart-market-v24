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
    """Avoid churn for PostgreSQL's equivalent unbounded VARCHAR/TEXT types."""
    string_types = (String, Text)
    if isinstance(inspected_type, string_types) and isinstance(metadata_type, string_types):
        inspected_length = getattr(inspected_type, "length", None)
        metadata_length = getattr(metadata_type, "length", None)
        if inspected_length is None and metadata_length is None:
            return False
    # None delegates all other comparisons to Alembic's normal comparator.
    return None


def _include_object(object_, name, type_, reflected, compare_to):
    # PostGIS owns this extension table; it is not part of the application schema.
    if type_ == "table" and name == "spatial_ref_sys" and reflected:
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
