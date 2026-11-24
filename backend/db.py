"""The UnderCover database: SQLite, seeded from the business data in data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_DB = Path(__file__).resolve().parent / "undercover.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    position INTEGER NOT NULL,
    status TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
    kind TEXT NOT NULL,
    id TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (kind, id)
);
CREATE TABLE IF NOT EXISTS decisions (
    claim_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    reason TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sign_offs (
    claim_id TEXT PRIMARY KEY,
    handler_id TEXT NOT NULL,
    signed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    claim_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    at TEXT NOT NULL
);
"""

TABLES = ["claims", "records", "decisions", "sign_offs", "payments", "steps"]


def path() -> Path:
    """Return the database file, from UNDERCOVER_DB or the default."""
    return Path(os.getenv("UNDERCOVER_DB") or DEFAULT_DB)


def connect() -> sqlite3.Connection:
    """Open the database with rows that read like dictionaries."""
    conn = sqlite3.connect(path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def database() -> Iterator[sqlite3.Connection]:
    """Yield a connection for one request, committing at the end."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def load(name: str) -> Any:
    """Load one JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed(conn: sqlite3.Connection) -> None:
    """Fill the database from the insurer's systems in data/."""
    for position, claim in enumerate(load("claims.json")):
        del claim["status"]
        conn.execute(
            "INSERT INTO claims VALUES (?, ?, 'waiting', ?)",
            (claim["claim_id"], position, json.dumps(claim)),
        )
    records = [
        ("policy", "policy_id", load("policies.json")),
        ("customer", "customer_id", load("customers.json")),
        ("handler", "handler_id", load("handlers.json")),
    ]
    for kind, key, rows in records:
        conn.executemany(
            "INSERT INTO records VALUES (?, ?, ?)",
            [(kind, row[key], json.dumps(row)) for row in rows],
        )
    conn.execute(
        "INSERT INTO records VALUES ('settings', 'plans', ?)",
        (json.dumps(load("plans.json")),),
    )
    conn.execute(
        "INSERT INTO records VALUES ('settings', 'company', ?)",
        (json.dumps(load("company.json")),),
    )


def init() -> None:
    """Create the tables, and seed them if the database is new."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0:
            seed(conn)
    conn.close()


def reset() -> None:
    """Drop everything and seed the database afresh."""
    with connect() as conn:
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")  # noqa: S608
    conn.close()
    init()


def record(conn: sqlite3.Connection, kind: str, record_id: str) -> Any | None:
    """Return one record of a kind, such as a policy, or None."""
    row = conn.execute(
        "SELECT body FROM records WHERE kind = ? AND id = ?", (kind, record_id)
    ).fetchone()
    return json.loads(row["body"]) if row else None


def records(conn: sqlite3.Connection, kind: str) -> list[Any]:
    """Return every record of a kind."""
    rows = conn.execute(
        "SELECT body FROM records WHERE kind = ? ORDER BY id", (kind,)
    ).fetchall()
    return [json.loads(row["body"]) for row in rows]


def setting(conn: sqlite3.Connection, name: str) -> Any:
    """Return one of the insurer's settings: plans or company."""
    row = conn.execute(
        "SELECT body FROM records WHERE kind = 'settings' AND id = ?", (name,)
    ).fetchone()
    return json.loads(row["body"])
