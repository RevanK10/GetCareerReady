import sqlite3
from contextlib import contextmanager

DB_PATH = "careerready.db"
STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]


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