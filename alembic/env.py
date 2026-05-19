import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.base import Base  # noqa: E402

# Import all models so Base.metadata knows about them
from app.model.channel_model import Channel  # noqa: E402, F401
from app.model.channel_video_model import ChannelVideo  # noqa: E402, F401
from app.model.job_model import Job  # noqa: E402, F401
from app.model.project_model import Project  # noqa: E402, F401
from app.model.scene_instruction_model import SceneInstruction  # noqa: E402, F401
from app.model.scene_model import Scene  # noqa: E402, F401
from app.model.variation_model import Variation  # noqa: E402, F401
from app.model.workflow_edge_model import WorkflowEdge  # noqa: E402, F401
from app.model.workflow_node_model import WorkflowNode  # noqa: E402, F401
from app.settings import settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Escape `%` to `%%` because alembic uses ConfigParser interpolation, and a
# URL-encoded DB password may contain `%`-sequences.
config.set_main_option("sqlalchemy.url", settings.sync_database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
