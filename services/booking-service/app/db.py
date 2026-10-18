"""Database connection pool.
A pool keeps a few connections open and reuses them (opening a new one for every request is slow).
`with pool.connection() as conn:` = one transaction: it commits at the end and rolls back if an error is raised."""
import os
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=int(os.getenv("DB_POOL_MAX", "10")),
    kwargs={"row_factory": dict_row},   # rows come back as dicts
    max_idle=120,                       # recycle idle connections before a serverless DB (Neon) suspends them
    check=ConnectionPool.check_connection,  # test a connection before handing it out; replace it if dead
    open=False,                         # opened at startup, see main.py
)
