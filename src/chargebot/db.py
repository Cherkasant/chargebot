import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional


DB_PRAGMA_STATEMENTS: list[tuple[str, tuple]] = [
    ("PRAGMA journal_mode=WAL;", tuple()),
    ("PRAGMA synchronous=NORMAL;", tuple()),
    ("PRAGMA foreign_keys=ON;", tuple()),
]


def ensure_sqlite_path(db_url: str) -> str:
    if not db_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// URL is supported by this simple DB layer")
    file_path = db_url.removeprefix("sqlite:///")
    Path(os.path.dirname(file_path) or ".").mkdir(parents=True, exist_ok=True)
    return file_path


def init_db(db_url: str) -> None:
    db_file = ensure_sqlite_path(db_url)
    with sqlite3.connect(db_file) as conn:
        for sql, params in DB_PRAGMA_STATEMENTS:
            conn.execute(sql)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stations (
                id INTEGER PRIMARY KEY,
                ext_id TEXT NOT NULL,
                name TEXT,
                address TEXT,
                operator TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                power_kw REAL,
                status TEXT,
                last_seen_utc TEXT,
                UNIQUE(ext_id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stations_lat_lon
            ON stations(latitude, longitude);
            """
        )
        conn.commit()


@contextmanager
def get_conn(db_url: str):
    db_file = ensure_sqlite_path(db_url)
    conn = sqlite3.connect(db_file)
    try:
        for sql, params in DB_PRAGMA_STATEMENTS:
            conn.execute(sql)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_stations(
    db_url: str,
    rows: Iterable[tuple[str, Optional[str], Optional[str], Optional[str], float, float, Optional[float], Optional[str], Optional[str]]],
) -> None:
    """
    Upsert stations by ext_id.
    Row order: ext_id, name, address, operator, lat, lon, power_kw, status, last_seen_utc
    """
    with get_conn(db_url) as conn:
        conn.executemany(
            """
            INSERT INTO stations (ext_id, name, address, operator, latitude, longitude, power_kw, status, last_seen_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ext_id) DO UPDATE SET
                name=excluded.name,
                address=excluded.address,
                operator=excluded.operator,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                power_kw=excluded.power_kw,
                status=excluded.status,
                last_seen_utc=excluded.last_seen_utc
            ;
            """,
            list(rows),
        )


