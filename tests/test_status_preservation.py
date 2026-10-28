
import pytest

from src.database.db import JobDataBase
from src.database.job_repository import JobRepository


def test_existing_review_status_is_preserved_after_job_update(tmp_path):
    database_path = str(tmp_path / "test_status.db")

    database = JobDataBase(database_path)
    database.create_table()

    repository = JobRepository(database_path)

    job_url = "https://test.com/status-preservation"

    job = {
        "title": "Data Analyst",
        "company": "Test Company",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": job_url,
        "description": "Original description",
        "skills": ["Python", "SQL"],
        "match_score": 90,
        "status": "FOUND",
        "source": "TEST",
    }

    repository.add_job(job)
    repository.update_status(job_url, "REVIEW")

    updated_job = {
        "title": "Data Analyst - Updated",
        "company": "Updated Company",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": job_url,
        "description": "Updated description",
        "skills": ["Python", "SQL", "Power BI"],
        "match_score": 95,
        "source": "Naukri",
    }

    assert repository.update_job(updated_job) is True

    stored_job = repository.get_job_by_url(job_url)

    assert stored_job is not None
    assert stored_job["title"] == "Data Analyst - Updated"
    assert stored_job["match_score"] == 95
    assert stored_job["status"] == "REVIEW"
