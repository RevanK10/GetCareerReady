import sqlite3
from contextlib import contextmanager

DB_PATH = "careerready.db"
STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]
JOB_FIELDS = ["url", "title", "company", "description", "score", "status",
              "fit_json", "resume_md", "resume_notes", "cover_letter", "error"]
JOB_EXTRA_COLUMNS = {
    "url": "TEXT DEFAULT ''",
    "fit_json": "TEXT DEFAULT ''",
    "resume_md": "TEXT DEFAULT ''",
    "resume_notes": "TEXT DEFAULT ''",
    "cover_letter": "TEXT DEFAULT ''",
    "error": "TEXT DEFAULT ''",
}
PROFILE_FIELDS = ["full_name", "email", "phone", "location", "links", "resume_text"]


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT,
                   company TEXT,
                   description TEXT,
                   score INTEGER,
                   status TEXT NOT NULL DEFAULT 'Saved',
                   created_at TEXT DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS profile (
                   id INTEGER PRIMARY KEY CHECK (id = 1),
                   full_name TEXT DEFAULT '',
                   email TEXT DEFAULT '',
                   phone TEXT DEFAULT '',
                   location TEXT DEFAULT '',
                   links TEXT DEFAULT '',
                   resume_text TEXT DEFAULT ''
               )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   job_id INTEGER NOT NULL,
                   step TEXT,
                   status TEXT,
                   message TEXT DEFAULT '',
                   created_at TEXT DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        _ensure_columns(conn, "jobs", JOB_EXTRA_COLUMNS)

def _ensure_columns(conn, table, columns):
    """Add any missing columns, so an older database file keeps working."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def get_profile():
    with connect() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    data = {f: "" for f in PROFILE_FIELDS}
    if row:
        data.update({f: row[f] or "" for f in PROFILE_FIELDS})
    return data


def save_profile(data):
    values = [str(data.get(f, "")) for f in PROFILE_FIELDS]
    cols = ", ".join(PROFILE_FIELDS)
    marks = ", ".join("?" for _ in PROFILE_FIELDS)
    updates = ", ".join(f"{f} = excluded.{f}" for f in PROFILE_FIELDS)
    with connect() as conn:
        conn.execute(
            f"INSERT INTO profile (id, {cols}) VALUES (1, {marks}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            values,
        )


def save_job(title, company, description, score, status="Saved"):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (title, company, description, score, status) VALUES (?, ?, ?, ?, ?)",
            (title, company, description, score, status),
        )
        return cur.lastrowid


def list_jobs():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def update_status(job_id, status):
    with connect() as conn:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))


def delete_job(job_id):
    with connect() as conn:
        conn.execute("DELETE FROM events WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def create_job(url="", description=""):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (url, description) VALUES (?, ?)", (url, description)
        )
        return cur.lastrowid


def get_job(job_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def update_job(job_id, **fields):
    unknown = set(fields) - set(JOB_FIELDS)
    if unknown:
        raise ValueError(f"Unknown job fields: {sorted(unknown)}")
    if not fields:
        return
    sets = ", ".join(f"{name} = ?" for name in fields)
    with connect() as conn:
        conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", [*fields.values(), job_id])


def add_event(job_id, step, status, message=""):
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (job_id, step, status, message) VALUES (?, ?, ?, ?)",
            (job_id, step, status, message),
        )


def list_events(job_id, limit=30):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY id DESC LIMIT ?", (job_id, limit)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]