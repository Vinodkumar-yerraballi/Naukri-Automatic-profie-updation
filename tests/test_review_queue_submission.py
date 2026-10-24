from src.application.application_tracker import ApplicationTracker
from src.application.review_queue import ReviewQueue
from src.database.job_repository import JobRepository


def test_submission_callback_runs_only_after_terminal_approval(
    tmp_path,
    monkeypatch,
):
    repository = JobRepository(tmp_path / "jobs.db")
    job = {
        "title": "Data Analyst",
        "company": "Example Co",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": "https://www.naukri.com/job-listing",
        "description": "Python and SQL",
        "skills": ["Python", "SQL"],
        "match_score": 90,
        "status": "REVIEW",
        "source": "Naukri",
    }
    repository.add_job(job)
    tracker = ApplicationTracker(repository)
    queue = ReviewQueue(repository, tracker)
    submissions = []
    answers = iter(("1", "a"))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    def submit_approved_job(selected_job):
        submissions.append(selected_job["job_url"])
        return {"status": "APPLIED", "message": "Confirmed"}

    queue.review_jobs_interactively(
        submission_callback=submit_approved_job
    )

    assert submissions == [job["job_url"]]
    assert repository.get_job_by_url(job["job_url"])["status"] == "APPROVED"
