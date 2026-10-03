from src.database.db import JobDataBase
from src.database.job_repository import JobRepository
from src.application.application_tracker import ApplicationTracker


def main():
    database = JobDataBase("data/test_tracker.db")
    database.create_table()

    repository = JobRepository("data/test_tracker.db")
    tracker = ApplicationTracker(repository)

    job_url = "https://test.com/tracker-test-job"

    # Create a test job
    job = {
        "title": "Data Analyst",
        "company": "Test Company",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": job_url,
        "description": "Test job for ApplicationTracker",
        "skills": "Python, SQL",
        "match_score": 90,
        "source": "TEST"
    }

    repository.add_job(job)

    # REVIEW
    tracker.mark_review(job_url)
    print("After REVIEW:", tracker.get_application_status(job_url))

    # APPROVED
    tracker.mark_approved(job_url)
    print("After APPROVED:", tracker.get_application_status(job_url))

    # APPLIED
    tracker.mark_applied(job_url)
    print("After APPLIED:", tracker.get_application_status(job_url))

    # REJECTED
    tracker.mark_rejected(job_url)
    print("After REJECTED:", tracker.get_application_status(job_url))


if __name__ == "__main__":
    main()