"""SQLite storage for connection history and known destinations.

The database lives at ~/.fosseverything/network_monitor.db so it is easy to
find, back up, or delete outright to wipe all history.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS destinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL UNIQUE,
    domain TEXT,
    first_seen TEXT NOT NULL,
    known INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS connection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    pid INTEGER,
    process_name TEXT,
    local_port INTEGER,
    remote_ip TEXT,
    remote_domain TEXT,
    remote_port INTEGER,
    protocol TEXT,
    bytes_sent INTEGER NOT NULL DEFAULT 0,
    bytes_recv INTEGER NOT NULL DEFAULT 0,
    is_new_destination INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_log_timestamp ON connection_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_log_process ON connection_log(process_name);
CREATE INDEX IF NOT EXISTS idx_log_domain ON connection_log(remote_domain);
"""


def app_data_dir() -> str:
    path = os.path.join(os.path.expanduser("~"), ".fosseverything")
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    return os.path.join(app_data_dir(), "network_monitor.db")


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # noqa: 21 (read internally by sqlite3, not by our code)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA)
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConnectionEvent:
    timestamp: str
    pid: int | None
    process_name: str
    local_port: int | None
    remote_ip: str
    remote_domain: str | None
    remote_port: int | None
    protocol: str
    bytes_sent: int
    bytes_recv: int
    is_new_destination: bool


def record_destination(conn: sqlite3.Connection, ip: str, domain: str | None) -> tuple[bool, bool]:
    """Insert `ip` into the known-destinations table if new.

    Returns (is_new, is_known) without a separate round-trip for the known flag.
    """
    row = conn.execute("SELECT id, domain, known FROM destinations WHERE ip = ?", (ip,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO destinations (ip, domain, first_seen, known) VALUES (?, ?, ?, 0)",
            (ip, domain, now_iso()),
        )
        return True, False
    if domain and not row["domain"]:
        conn.execute("UPDATE destinations SET domain = ? WHERE id = ?", (domain, row["id"]))
    return False, bool(row["known"])


def is_known(conn: sqlite3.Connection, ip: str) -> bool:
    row = conn.execute("SELECT known FROM destinations WHERE ip = ?", (ip,)).fetchone()
    return bool(row and row["known"])


def mark_destination_known(conn: sqlite3.Connection, ip: str) -> None:
    conn.execute("UPDATE destinations SET known = 1 WHERE ip = ?", (ip,))
    conn.commit()


def cached_domains(conn: sqlite3.Connection) -> dict[str, str | None]:
    rows = conn.execute("SELECT ip, domain FROM destinations").fetchall()
    return {row["ip"]: row["domain"] for row in rows}


def unknown_destinations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT ip, domain, first_seen FROM destinations WHERE known = 0 ORDER BY first_seen DESC"
    ).fetchall()


def log_connection(conn: sqlite3.Connection, event: ConnectionEvent) -> None:
    conn.execute(
        """INSERT INTO connection_log
           (timestamp, pid, process_name, local_port, remote_ip, remote_domain,
            remote_port, protocol, bytes_sent, bytes_recv, is_new_destination)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.timestamp, event.pid, event.process_name, event.local_port,
            event.remote_ip, event.remote_domain, event.remote_port, event.protocol,
            event.bytes_sent, event.bytes_recv, int(event.is_new_destination),
        ),
    )


def search_history(
    conn: sqlite3.Connection,
    process_name: str = "",
    domain: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 1000,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM connection_log WHERE 1=1"
    params: list[object] = []
    if process_name:
        query += " AND process_name LIKE ?"
        params.append(f"%{process_name}%")
    if domain:
        query += " AND (remote_domain LIKE ? OR remote_ip LIKE ?)"
        params.extend([f"%{domain}%", f"%{domain}%"])
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()


def top_processes(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT process_name, COUNT(*) as connection_count
           FROM connection_log
           GROUP BY process_name
           ORDER BY connection_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()


def top_domains(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT COALESCE(remote_domain, remote_ip) as destination, COUNT(*) as connection_count
           FROM connection_log
           GROUP BY destination
           ORDER BY connection_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()


def connections_over_time(conn: sqlite3.Connection, days: int = 7) -> list[sqlite3.Row]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return conn.execute(
        """SELECT substr(timestamp, 1, 10) as day, COUNT(*) as connection_count
           FROM connection_log
           WHERE timestamp >= ?
           GROUP BY day
           ORDER BY day ASC""",
        (since,),
    ).fetchall()


def per_app_summary(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT process_name,
                  COUNT(*) as total_connections,
                  COUNT(DISTINCT COALESCE(remote_domain, remote_ip)) as unique_domains,
                  MAX(timestamp) as last_seen
           FROM connection_log
           GROUP BY process_name
           ORDER BY total_connections DESC"""
    ).fetchall()


def prune_older_than(conn: sqlite3.Connection, days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor = conn.execute("DELETE FROM connection_log WHERE timestamp < ?", (cutoff,))
    conn.commit()
    return cursor.rowcount


def wipe_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM connection_log")
    conn.execute("DELETE FROM destinations")
    conn.commit()
