"""Migration credentials are read only from the environment, never from Git."""
from alembic import context
from sqlalchemy import create_engine, pool
from progress_history import database_url, metadata

url = database_url()
if url is None:
    raise RuntimeError("Set JOURNEY_DATABASE_URL before running migrations.")

if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True,
                           connect_args={"connect_timeout": 3})
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
