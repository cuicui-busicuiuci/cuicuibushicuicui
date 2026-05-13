import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            isolation_level=None,
        )
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA synchronous=NORMAL")
        _connection.execute("PRAGMA cache_size=-64000")
        _connection.row_factory = sqlite3.Row
    return _connection


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        pass


def init_db():
    from app.db.schema import create_tables
    conn = get_connection()
    create_tables(conn)
