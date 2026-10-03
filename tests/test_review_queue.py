import os

from src.database.db import JobDataBase
from src.database.job_repository import JobRepository
from src.application.application_tracker import ApplicationTracker
from src.application.review_queue import ReviewQueue


def main():
    database_path = "data/test_review_queue.db"

    if os.path.exists(database_path):
        os.remove(database_path)

    database = JobDataBase(database_path)
    database.create_table()

    repository = JobRepository(database_path)

    application_tracker = ApplicationTracker(
        repository
    )

    review_queue = ReviewQueue(
        repository,
        application_tracker
    )

    jobs = [
        {
            "title": "Data Analyst",
            "company": "Company A",
            "location": "Remote",
            "experience": "0-2 years",
            "job_url": "https://test.com/queue-1",
            "description": "Test job 1",
            "skills": ["Python", "SQL"],
            "match_score": 90,
            "status": "REVIEW",
            "source": "Naukri"
        },
        {
            "title": "Data Scientist",
            "company": "Company B",
            "location": "Bangalore",
            "experience": "1-2 years",
            "job_url": "https://test.com/queue-2",
            "description": "Test job 2",
            "skills": ["Python", "Machine Learning"],
            "match_score": 85,
            "status": "REVIEW",
            "source": "Naukri"
        }
    ]

    for job in jobs:
        repository.add_job(job)

    pending_jobs = review_queue.get_pending_jobs()

    print("\n========== PENDING JOBS ==========")

    for job in pending_jobs:
        print(
            job["title"],
            "|",
            job["company"],
            "|",
            job["match_score"],
            "|",
            job["status"]
        )

    print("\nPending jobs:", len(pending_jobs))

    approve_result = review_queue.approve_job(
        "https://test.com/queue-1"
    )

    print("\nApprove result:", approve_result)

    approved_job = repository.get_job_by_url(
        "https://test.com/queue-1"
    )

    print(
        "Approved job status:",
        approved_job["status"]
    )

    reject_result = review_queue.reject_job(
        "https://test.com/queue-2"
    )

    print("\nReject result:", reject_result)

    rejected_job = repository.get_job_by_url(
        "https://test.com/queue-2"
    )

    print(
        "Rejected job status:",
        rejected_job["status"]
    )

    remaining_jobs = review_queue.get_pending_jobs()

    print(
        "\nRemaining REVIEW jobs:",
        len(remaining_jobs)
    )

    if (
        len(pending_jobs) == 2
        and approve_result is True
        and approved_job["status"] == "APPROVED"
        and reject_result is True
        and rejected_job["status"] == "REJECTED"
        and len(remaining_jobs) == 0
    ):
        print(
            "\nTEST PASSED: "
            "Review Queue workflow works correctly."
        )
    else:
        print(
            "\nTEST FAILED: "
            "Review Queue workflow has an issue."
        )


if __name__ == "__main__":
    main()