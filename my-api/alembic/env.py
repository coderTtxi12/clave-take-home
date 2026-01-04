from logging.config import fileConfig
import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Load environment variables from .env file in project root
# alembic/ is in my-api/alembic/, so we go up 2 levels to reach project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.models.database import Base
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variables if present
# Prefer Supabase configuration if available, otherwise use local PostgreSQL
supabase_db_host = os.getenv("SUPABASE_DB_HOST")
if supabase_db_host:
    # Use Supabase configuration
    # Supabase default database name is 'postgres', not 'restaurant_analytics'
    db_host = supabase_db_host
    db_port = os.getenv("SUPABASE_DB_PORT", "5432")
    db_name = os.getenv("SUPABASE_DB_NAME", os.getenv("DB_NAME", "postgres"))
    db_user = os.getenv("SUPABASE_DB_USER", os.getenv("DB_USER", "postgres"))
    db_password = os.getenv("SUPABASE_DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
    if not db_password:
        raise ValueError("SUPABASE_DB_PASSWORD must be set when using Supabase")
else:
    # Use local PostgreSQL configuration
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5433")
    db_name = os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "restaurant_analytics"))
    db_user = os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres"))
    db_password = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "postgres"))

# URL-encode password to handle special characters like @, #, /, etc.
encoded_password = quote_plus(db_password)
database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

# Set the database URL directly, escaping % for ConfigParser
# ConfigParser interprets % as interpolation, so we need to double them
escaped_url = database_url.replace('%', '%%')
config.set_main_option("sqlalchemy.url", escaped_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
