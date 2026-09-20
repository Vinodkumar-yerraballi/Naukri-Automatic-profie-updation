from src.application.application_workflow import ApplicationWorkflow
from src.application.permission import PermissionManager
from src.application.application_tracker import ApplicationTracker
from src.application.captcha_handler import CaptchaHandler
from src.database.job_repository import JobRepository
from src.notification.notifier import Notifier


def main():

    print("\n========== APPLICATION WORKFLOW TEST ==========")

    repository = JobRepository(
        "data/job_automation.db"
    )

    permission_manager = PermissionManager(
        minimum_score=85,
        auto_apply=False
    )

    tracker = ApplicationTracker(
        repository
    )

    captcha_handler = CaptchaHandler()

    notifier = Notifier()

    workflow = ApplicationWorkflow(
        permission_manager=permission_manager,
        application_tracker=tracker,
        captcha_handler=captcha_handler,
        notifier=notifier
    )

    test_job = {
        "title": "Data Analyst",
        "company": "ABC Technologies",
        "job_url": "https://example.com/jobs/data-analyst-001",
        "match_score": 92.0
    }

    result = workflow.process_job(
        job=test_job,
        page_text="Normal job application page"
    )

    print("\n========== WORKFLOW RESULT ==========")
    print(result)


if __name__ == "__main__":
    main()