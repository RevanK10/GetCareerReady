import sqlite3
from contextlib import contextmanager

DB_PATH = "careerready.db"
STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]
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
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))