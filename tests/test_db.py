import sqlite3

import pytest

import db


def test_profile_upsert(tmp_db):
    assert tmp_db.get_profile()["full_name"] == "Jane Doe"
    tmp_db.save_profile({"full_name": "Jane D", "email": "j@x.com"})
    profile = tmp_db.get_profile()
    assert profile["full_name"] == "Jane D" and profile["email"] == "j@x.com" and profile["resume_text"] == ""


def test_profile_empty_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "empty.db"))
    db.init_db()
    assert db.get_profile()["resume_text"] == ""


def test_sql_injection_text_is_stored_as_plain_text(tmp_db):
    job_id = tmp_db.create_job("", "x'; DROP TABLE jobs;--")
    assert tmp_db.get_job(job_id)["description"] == "x'; DROP TABLE jobs;--"
    assert len(tmp_db.list_jobs()) == 1


def test_update_job_rejects_unknown_columns(tmp_db):
    job_id = tmp_db.create_job("", "d")
    with pytest.raises(ValueError):
        tmp_db.update_job(job_id, evil="x")
    tmp_db.update_job(job_id, title="Eng", score=80)
    assert tmp_db.get_job(job_id)["title"] == "Eng"


def test_get_missing_job(tmp_db):
    assert tmp_db.get_job(999) is None


def test_delete_job_removes_events(tmp_db):
    job_id = tmp_db.create_job("", "d")
    tmp_db.add_event(job_id, "fit", "start")
    tmp_db.delete_job(job_id)
    assert tmp_db.list_events(job_id) == [] and tmp_db.get_job(job_id) is None


def test_events_keep_order_and_limit(tmp_db):
    job_id = tmp_db.create_job("", "d")
    for i in range(5):
        tmp_db.add_event(job_id, "s", "start", str(i))
    assert [e["message"] for e in tmp_db.list_events(job_id, limit=3)] == ["2", "3", "4"]


def test_old_database_is_migrated_in_place(tmp_path, monkeypatch):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, "
                 "description TEXT, score INTEGER, status TEXT NOT NULL DEFAULT 'Saved', created_at TEXT)")
    conn.execute("INSERT INTO jobs (title, company, description, score) VALUES ('Old', 'Co', 'desc', 50)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    db.init_db()  # safe to run twice
    job = db.get_job(1)
    assert job["title"] == "Old" and job["score"] == 50
    assert job["fit_json"] == "" and job["review_json"] == ""
