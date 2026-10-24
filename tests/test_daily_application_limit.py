import sqlite3

from src.application.application_tracker import ApplicationTracker
from src.database.job_repository import JobRepository


def test_confirmed_application_is_counted_toward_today_limit(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    job_url = "https://www.naukri.com/job-listing"
    repository.add_job(
        {
            "title": "Data Analyst",
            "job_url": job_url,
            "status": "APPROVED",
            "source": "Naukri",
        }
    )
    tracker = ApplicationTracker(repository)

    assert repository.get_application_attempt_count_today() == 0
    tracker.mark_applied(job_url)

    assert repository.get_application_attempt_count_today() == 1
    job = repository.get_job_by_url(job_url)
    assert job["status"] == "APPLIED"
    assert job["date_applied"]
    assert job["date_application_attempted"]


def test_uncertain_submission_counts_toward_daily_limit(tmp_path):
    repository = JobRepository(tmp_path / "jobs.db")
    job_url = "https://www.naukri.com/job-listing"
    repository.add_job(
        {
            "title": "Data Analyst",
            "job_url": job_url,
            "status": "APPROVED",
            "source": "Naukri",
        }
    )
    tracker = ApplicationTracker(repository)

    tracker.mark_application_unconfirmed(job_url)

    assert repository.get_application_attempt_count_today() == 1


def test_existing_database_gets_application_attempt_timestamp_column(
    tmp_path,
):
    database_path = tmp_path / "legacy-jobs.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            experience TEXT,
            job_url TEXT UNIQUE,
            description TEXT,
            skills TEXT,
            match_score REAL,
            status TEXT,
            source TEXT,
            date_found TEXT,
            date_applied TEXT
        )
        """
    )
    connection.commit()
    connection.close()

    repository = JobRepository(database_path)
    connection = repository.database.get_connection()
    columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
    connection.close()

    assert "date_application_attempted" in columns
