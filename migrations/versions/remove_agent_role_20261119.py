"""Remove the AGENT role and deal assignment."""

from alembic import op
import sqlalchemy as sa


revision: str = "remove_agent_role_20261119"
down_revision: str = "20261027_push_lang"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Check table existence before querying their columns or data.
    tables = bind.execute(sa.text("""
        SELECT
            to_regclass('public.users') IS NOT NULL AS users_exists,
            to_regclass('public.deals') IS NOT NULL AS deals_exists
    """)).mappings().one()

    if not tables["users_exists"] or not tables["deals_exists"]:
        raise RuntimeError("Expected public.users and public.deals tables.")

    columns = bind.execute(sa.text("""
        SELECT
            EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'role'
                  AND udt_schema = 'public'
                  AND udt_name = 'userrole'
            ) AS role_column_valid,
            EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'deals'
                  AND column_name = 'agent_id'
                  AND data_type = 'integer'
                  AND is_nullable = 'YES'
            ) AS agent_column_valid,
            EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public'
                  AND t.typname = 'userrole'
                  AND t.typtype = 'e'
            ) AS enum_exists
    """)).mappings().one()

    if not columns["enum_exists"]:
        raise RuntimeError("Expected PostgreSQL enum public.userrole.")
    if not columns["role_column_valid"]:
        raise RuntimeError("users.role does not use public.userrole.")
    if not columns["agent_column_valid"]:
        raise RuntimeError(
            "Expected nullable integer column public.deals.agent_id."
        )

    labels = bind.execute(sa.text("""
        SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)
        FROM pg_enum e
        JOIN pg_type t ON t.oid = e.enumtypid
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public'
          AND t.typname = 'userrole'
    """)).scalar_one()

    if labels != ["ADMIN", "MERCHANT", "BUYER", "AGENT"]:
        raise RuntimeError(
            f"Unexpected public.userrole labels: {labels!r}"
        )

    # Verify the exact historical foreign key before dropping it.
    foreign_key_exists = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_attribute src
              ON src.attrelid = c.conrelid
             AND src.attname = 'agent_id'
            JOIN pg_attribute dst
              ON dst.attrelid = c.confrelid
             AND dst.attname = 'id'
            WHERE c.conname = 'fk_deals_agent_id_users'
              AND c.contype = 'f'
              AND c.conrelid = 'public.deals'::regclass
              AND c.confrelid = 'public.users'::regclass
              AND c.conkey = ARRAY[src.attnum]::smallint[]
              AND c.confkey = ARRAY[dst.attnum]::smallint[]
              AND c.confdeltype = 'n'
              AND c.convalidated
        )
    """)).scalar_one()

    if not foreign_key_exists:
        raise RuntimeError(
            "Expected validated FK fk_deals_agent_id_users was not found."
        )

    # Verify the exact single-column, non-unique historical index.
    index_exists = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_class idx
            JOIN pg_namespace ns ON ns.oid = idx.relnamespace
            JOIN pg_index i ON i.indexrelid = idx.oid
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attname = 'agent_id'
            WHERE ns.nspname = 'public'
              AND idx.relname = 'ix_deals_agent_id'
              AND i.indrelid = 'public.deals'::regclass
              AND i.indisvalid
              AND NOT i.indisunique
              AND i.indnatts = 1
              AND i.indnkeyatts = 1
              AND i.indkey::smallint[] = ARRAY[a.attnum]::smallint[]
        )
    """)).scalar_one()

    if not index_exists:
        raise RuntimeError(
            "Expected single-column index ix_deals_agent_id was not found."
        )

    # SQLAlchemy's model uses a Python default, not a server-side default.
    has_server_default = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attrdef d
              ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE n.nspname = 'public'
              AND c.relname = 'users'
              AND a.attname = 'role'
              AND NOT a.attisdropped
        )
    """)).scalar_one()

    if has_server_default:
        raise RuntimeError(
            "Unexpected server default on users.role; inspect before migration."
        )

    # Refuse to discard any existing AGENT users or assigned deals.
    has_agent_users = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM public.users
            WHERE role::text = 'AGENT'
        )
    """)).scalar_one()

    if has_agent_users:
        raise RuntimeError(
            "Cannot remove AGENT role: users with role AGENT still exist."
        )

    has_assigned_deals = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM public.deals
            WHERE agent_id IS NOT NULL
        )
    """)).scalar_one()

    if has_assigned_deals:
        raise RuntimeError(
            "Cannot remove agent assignment: deals.agent_id is not empty."
        )

    op.drop_constraint(
        "fk_deals_agent_id_users",
        "deals",
        type_="foreignkey",
    )
    op.drop_index("ix_deals_agent_id", table_name="deals")
    op.drop_column("deals", "agent_id")

    # Replace the enum without CASCADE. PostgreSQL must reject unexpected
    # remaining dependencies rather than silently removing them.
    op.execute(
        "ALTER TYPE public.userrole RENAME TO userrole_with_agent_old"
    )
    op.execute(
        "CREATE TYPE public.userrole "
        "AS ENUM ('ADMIN', 'MERCHANT', 'BUYER')"
    )
    op.execute("""
        ALTER TABLE public.users
        ALTER COLUMN role TYPE public.userrole
        USING role::text::public.userrole
    """)
    op.execute("DROP TYPE public.userrole_with_agent_old")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE public.userrole_with_agent_new "
        "AS ENUM ('ADMIN', 'MERCHANT', 'BUYER', 'AGENT')"
    )
    op.execute("""
        ALTER TABLE public.users
        ALTER COLUMN role TYPE public.userrole_with_agent_new
        USING role::text::public.userrole_with_agent_new
    """)
    op.execute("DROP TYPE public.userrole")
    op.execute(
        "ALTER TYPE public.userrole_with_agent_new RENAME TO userrole"
    )

    op.add_column(
        "deals",
        sa.Column("agent_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_deals_agent_id",
        "deals",
        ["agent_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_deals_agent_id_users",
        "deals",
        "users",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
