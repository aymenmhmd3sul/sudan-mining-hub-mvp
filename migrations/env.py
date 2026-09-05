from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.db.session import Base

# Import canonical models only.
import app.db.base  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

CANONICAL_TABLES = {
    "users",
    "listing_categories",
    "listings",
    "listing_locations",
    "listing_media",
    "listing_specs",
    "buyer_requests",
    "request_items",
    "offers",
    "negotiation_rooms",
    "negotiation_participants",
    "negotiation_messages",
    "deals",
    "commissions",
    "commission_settings",
}


def include_object(
    object,
    name,
    type_,
    reflected,
    compare_to,
):
    if type_ == "table":
        return name in CANONICAL_TABLES

    if type_ == "column":
        table = getattr(object, "table", None)

        if table is not None:
            return table.name in CANONICAL_TABLES

    if type_ in {"index", "unique_constraint", "foreign_key_constraint"}:
        table = getattr(object, "table", None)

        if table is not None:
            return table.name in CANONICAL_TABLES

    return True


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}

    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
