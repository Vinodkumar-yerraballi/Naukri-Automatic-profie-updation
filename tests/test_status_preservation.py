from src.database.db import JobDataBase
from src.database.job_repository import JobRepository


def main():
    database_path = "data/test_status.db"

    database = JobDataBase(database_path)
    database.create_table()

    repository = JobRepository(database_path)

    job_url = "https://test.com/status-preservation"

    # Add the job
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
        "source": "TEST"
    }

    repository.add_job(job)

    # Manually move job to REVIEW
    repository.update_status(job_url, "REVIEW")

    print("Before update:")
    print(repository.get_job_by_url(job_url))

    # Simulate a new job update from JobCollector
    updated_job = {
        "title": "Data Analyst - Updated",
        "company": "Updated Company",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": job_url,
        "description": "Updated description",
        "skills": ["Python", "SQL", "Power BI"],
        "match_score": 95,
        "source": "Naukri"
    }

    repository.update_job(updated_job)

    print("\nAfter update:")
    print(repository.get_job_by_url(job_url))


if __name__ == "__main__":
    main()