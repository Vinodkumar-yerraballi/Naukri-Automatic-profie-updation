
from src.ingestion.naukri_browser import NaukriBrowser
from src.pipelines.job_pipeline import JobPipeline
from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.application.application_workflow import ApplicationWorkflow
from src.application.permission import PermissionManager
from src.application.application_tracker import ApplicationTracker
from src.application.captcha_handler import CaptchaHandler
from src.notification.notifier import Notifier
from src.profile.profile_updater import ProfileManager
from src.config.config_manager import ConfigManager


def main():
    browser = NaukriBrowser(headless=False)

    try:
        config_manager = ConfigManager()
        profile_manager = ProfileManager("config/profile.yaml")
        search_config = config_manager.get_job_search_config()

        evaluator = JobEvaluator(
            candidate_skills=profile_manager.get_all_skills(),
            target_roles=profile_manager.get_target_roles(),
            preferred_locations=search_config.get("locations", []),
            preferred_work_modes=search_config.get("work_modes", []),
            candidate_education=profile_manager.get_education()
        )

        repository = JobRepository("data/test_naukri_pipeline.db")
        collector = JobCollector(evaluator, repository)

        permission_manager = PermissionManager()
        tracker = ApplicationTracker(repository)
        captcha_handler = CaptchaHandler()
        notifier = Notifier()

        workflow = ApplicationWorkflow(
            permission_manager,
            tracker,
            captcha_handler,
            notifier
        )

        pipeline = JobPipeline(collector, workflow)

        browser.start()
        browser.open_naukri()

        role = "Data Analyst"
        location = "Bangalore"

        browser.search_jobs(role, location)

        if browser.detect_security_challenge():
            print("Security challenge detected. Complete it manually.")
            return

        jobs = browser.get_job_cards()

        print(f"\nJob cards found: {len(jobs)}")

        for index, job in enumerate(jobs[:3], start=1):
            print(f"\nProcessing job {index}: {job.get('title')}")

            if not job.get("job_url"):
                print("Skipping: missing job URL.")
                continue

            details = browser.extract_job_details(job)

            if details.get("security_challenge"):
                print("Security challenge detected. Stop and complete it manually.")
                break

            if details.get("extraction_error"):
                print("Skipping job due to extraction error.")
                continue

            description = details.get("job_description", "").strip()

            if not description:
                print("Skipping job because its description is empty.")
                continue

            result = pipeline.process_job(
                job_description=description,
                job_url=details["job_url"],
                source="Naukri",
                page_text=browser.get_visible_text(),
                job_metadata={
                    "title": details.get("title"),
                    "company": details.get("company"),
                    "location": details.get("location"),
                    "experience": details.get("experience"),
                    "posted": details.get("posted", ""),
                    "employment_type": details.get("employment_type"),
                    "education": details.get("education", [])
                }
            )

            print("Company:", result["job"].get("company"))
            print("Score:", result["job"].get("match_score"))
            print("Workflow status:", result["workflow"].get("status"))
            print("\n--- DEBUG: JOB EVALUATION ---")
            print("Job title:", result["job"].get("title"))
            print("Company:", result["job"].get("company"))
            print("Experience:", result["job"].get("experience"))
            print("Stored skills:", result["job"].get("skills"))
            print("Evaluation details:", result["evaluation"])
            print("Workflow result:", result["workflow"])
            print("-----------------------------")

    finally:
        browser.close()


if __name__ == "__main__":
    main()
