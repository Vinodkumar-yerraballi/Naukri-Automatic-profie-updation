import os

from src.database.db import JobDataBase
from src.database.job_repository import JobRepository
from src.application.application_tracker import ApplicationTracker
from src.application.review_queue import ReviewQueue


def main():
    database_path = "data/test_interactive_review.db"

    if os.path.exists(database_path):
        os.remove(database_path)

    database = JobDataBase(database_path)
    database.create_table()

    repository = JobRepository(database_path)
    tracker = ApplicationTracker(repository)

    job = {
        "title": "Data Analyst",
        "company": "Interactive Test Company",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": "https://test.com/interactive-review",
        "description": "Test interactive review",
        "skills": ["Python", "SQL"],
        "match_score": 90,
        "status": "REVIEW",
        "source": "TEST"
    }

    repository.add_job(job)

    review_queue = ReviewQueue(
        repository=repository,
        application_tracker=tracker
    )

    review_queue.review_jobs_interactively()

    print("\nFinal job status:")
    print(
        repository.get_job_by_url(
            "https://test.com/interactive-review"
        )
    )


if __name__ == "__main__":
    main()