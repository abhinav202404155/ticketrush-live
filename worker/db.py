"""Database connection pool.
A pool keeps a few connections open and reuses them (opening a new one for
every request is slow). `with pool.connection() as conn:` = one transaction:
it commits at the end and rolls back automatically if an error is raised."""
import os
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=int(os.getenv("DB_POOL_MAX", "10")),
    kwargs={"row_factory": dict_row},  # rows come back as dicts
    open=False,                        # opened at startup, see main.py
)
