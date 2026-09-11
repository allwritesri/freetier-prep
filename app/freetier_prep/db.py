"""SQLite manifest store.

Trust rule enforced by schema: the platform persists only the session
manifest (who, which project, which lab, state-bucket URI, TTL, status).
Terraform state and resource IDs never land here — state lives in the
student's bucket (see fake_gcp.py / provisioner.py).
"""

import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    project_id TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    lab_id TEXT NOT NULL,
    state_bucket_uri TEXT NOT NULL,
    ttl_deadline REAL NOT NULL,
    status TEXT NOT NULL,           -- active | ending | torn_down | teardown_failed
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS task_progress (
    user_id TEXT NOT NULL,
    lab_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,           -- validated
    validated_at REAL NOT NULL,
    PRIMARY KEY (user_id, lab_id, task_id)
);
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    lab_id TEXT NOT NULL,
    payload TEXT NOT NULL,          -- canonical JSON attestation
    signature TEXT NOT NULL,        -- ed25519 hex
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    resource_manifest TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # -- users -------------------------------------------------------------
    def upsert_user(self, email: str, project_id: str) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE users SET project_id = ? WHERE id = ?", (project_id, row["id"])
            )
            self.conn.commit()
            return self.get_user(row["id"])
        uid = new_id("user")
        self.conn.execute(
            "INSERT INTO users (id, email, project_id, created_at) VALUES (?,?,?,?)",
            (uid, email, project_id, time.time()),
        )
        self.conn.commit()
        return self.get_user(uid)

    def get_user(self, user_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    # -- sessions ----------------------------------------------------------
    def create_session(
        self, user_id: str, project_id: str, lab_id: str,
        state_bucket_uri: str, ttl_deadline: float,
    ) -> sqlite3.Row:
        sid = new_id("session")
        now = time.time()
        self.conn.execute(
            "INSERT INTO sessions (id, user_id, project_id, lab_id, state_bucket_uri,"
            " ttl_deadline, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, user_id, project_id, lab_id, state_bucket_uri,
             ttl_deadline, "active", now, now),
        )
        self.conn.commit()
        return self.get_session(sid)

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    def set_session_status(self, session_id: str, status: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), session_id),
        )
        self.conn.commit()

    def active_session_for_project(self, project_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE project_id = ? AND status IN"
            " ('active','ending') ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()

    def expired_active_sessions(self, now: float) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE status = 'active' AND ttl_deadline <= ?",
            (now,),
        ).fetchall()

    def all_sessions(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC"
        ).fetchall()

    # -- task progress (survives teardown; keyed off user+lab) -------------
    def mark_task_validated(self, user_id: str, lab_id: str, task_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO task_progress"
            " (user_id, lab_id, task_id, status, validated_at) VALUES (?,?,?,?,?)",
            (user_id, lab_id, task_id, "validated", time.time()),
        )
        self.conn.commit()

    def validated_tasks(self, user_id: str, lab_id: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT task_id FROM task_progress WHERE user_id = ? AND lab_id = ?"
            " AND status = 'validated'",
            (user_id, lab_id),
        ).fetchall()
        return {r["task_id"] for r in rows}

    # -- transcripts -------------------------------------------------------
    def save_transcript(
        self, user_id: str, lab_id: str, payload: str, signature: str
    ) -> str:
        tid = new_id("tr")
        self.conn.execute(
            "INSERT INTO transcripts (id, user_id, lab_id, payload, signature,"
            " created_at) VALUES (?,?,?,?,?,?)",
            (tid, user_id, lab_id, payload, signature, time.time()),
        )
        self.conn.commit()
        return tid

    def get_transcript(self, transcript_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM transcripts WHERE id = ?", (transcript_id,)
        ).fetchone()

    # -- notifications / escalations ---------------------------------------
    def notify(self, user_id: str, kind: str, message: str) -> None:
        self.conn.execute(
            "INSERT INTO notifications (user_id, kind, message, created_at)"
            " VALUES (?,?,?,?)",
            (user_id, kind, message, time.time()),
        )
        self.conn.commit()

    def notifications_for(self, user_id: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()

    def record_escalation(
        self, session_id: str, reason: str, resource_manifest: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO escalations (session_id, reason, resource_manifest,"
            " created_at) VALUES (?,?,?,?)",
            (session_id, reason, resource_manifest, time.time()),
        )
        self.conn.commit()

    def resolve_escalations(self, session_id: str) -> None:
        self.conn.execute(
            "UPDATE escalations SET resolved = 1 WHERE session_id = ?", (session_id,)
        )
        self.conn.commit()

    def escalations(self, unresolved_only: bool = False) -> list[sqlite3.Row]:
        q = "SELECT * FROM escalations"
        if unresolved_only:
            q += " WHERE resolved = 0"
        return self.conn.execute(q + " ORDER BY id DESC").fetchall()
