import argparse
from datetime import date

from src.ingestion.naukri_browser import NaukriBrowser
from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.config.config_manager import ConfigManager
from src.profile.profile_updater import ProfileManager
from src.application.application_workflow import ApplicationWorkflow
from src.application.application_tracker import ApplicationTracker
from src.application.review_queue import ReviewQueue
from src.application.captcha_handler import CaptchaHandler
from src.notification.notifier import Notifier
from src.application.permission import PermissionManager
from src.profile.resume_tailoring import ResumeTailoringService
from src.profile.naukri_resume_uploader import NaukriResumeUploader
from src.pipelines.daily_scheduler import run_daily
from src.matching.freshness_matcher import FreshnessMatcher


def main(run_review=True):

    print("\n========== NAUKRI JOB PIPELINE ==========")

    config_manager = ConfigManager()
    profile_config = config_manager.get_naukri_profile_config()
    resume_config = config_manager.get_resume_tailoring_config()
    profile_update_enabled = profile_config.get("update_resume", False)
    source_resume = profile_config.get(
        "resume_path",
        resume_config.get("resume_path", "data/resume.pdf"),
    )

    browser = NaukriBrowser(
        headless=False
    )

    try:

        resume_tailoring = ResumeTailoringService.from_config(resume_config)

        if resume_tailoring:
            print(
                "Resume tailoring is enabled. Drafts will be saved locally "
                "for manual review."
            )

        # ==================================================
        # 1. Start browser
        # ==================================================

        if profile_update_enabled:
            browser.start_persistent(
                profile_config.get(
                    "browser_profile_directory",
                    "data/naukri_browser_profile",
                )
            )
            try:
                uploader = NaukriResumeUploader(
                    profile_config.get(
                        "upload_state_file",
                        "data/profile_resume_upload.json",
                    )
                )
                uploaded = uploader.update_if_changed(
                    browser,
                    source_resume,
                )
                if uploaded:
                    print(
                        f"Naukri profile resume updated from: {source_resume}"
                    )
            except (OSError, RuntimeError, ValueError) as error:
                print(
                    "\nNaukri profile resume update failed; continuing with "
                    "job search: "
                    f"{type(error).__name__}: {error}"
                )
        else:
            browser.start()

        # ==================================================
        # 2. Search Naukri
        # ==================================================

        search_config = (
            config_manager.get_job_search_config()
        )

        roles = search_config.get("roles", [])
        locations = search_config.get("locations", [])
        if not roles or not locations:
            raise ValueError(
                "At least one target role and location must be configured."
            )

        search_queries = [
            (role, location)
            for role in roles
            for location in locations
        ]
        max_searches = max(
            1,
            int(
                search_config.get(
                    "max_searches_per_run", len(search_queries)
                )
            ),
        )
        first_query = date.today().toordinal() % len(search_queries)
        rotated_queries = (
            search_queries[first_query:] + search_queries[:first_query]
        )
        selected_queries = rotated_queries[:max_searches]

        # Rotate through configured role/location pairs to keep each daily run
        # bounded while covering all configured searches over time.
        jobs_by_url = {}
        posted_within_hours = int(
            search_config.get("posted_within_hours", 24)
        )
        freshness_matcher = FreshnessMatcher()
        for index, (role, location) in enumerate(selected_queries, start=1):
            print(
                f"\nSearch {index}/{len(selected_queries)}: "
                f"{role} in {location}"
            )
            browser.search_jobs(
                role=role,
                location=location,
                posted_within_hours=posted_within_hours,
            )
            if browser.detect_security_challenge():
                print(
                    "Security challenge detected. Stop the scheduled run "
                    "and complete it manually in the browser."
                )
                return
            for job_card in browser.get_job_cards():
                if not freshness_matcher.is_within_last_hours(
                    job_card.get("posted", ""),
                    max_hours=posted_within_hours,
                ):
                    print(
                        "Skipping listing with unknown or older posting age: "
                        f"{job_card.get('title', 'Unknown')} "
                        f"({job_card.get('posted') or 'age unavailable'})"
                    )
                    continue
                job_url = job_card.get("job_url")
                if job_url:
                    jobs_by_url.setdefault(job_url, job_card)

        # ==================================================
        # 3. Get unique job cards from the selected searches
        # ==================================================

        jobs = list(jobs_by_url.values())

        print(f"\nJobs found: {len(jobs)}")

        if not jobs:
            print("No jobs found.")
            return

        # ==================================================
        # 4. Select first 20 jobs
        # ==================================================

        jobs_to_process = jobs[:20]

        print(
            f"\nProcessing {len(jobs_to_process)} jobs..."
        )

        # ==================================================
        # 5. Load candidate profile
        # ==================================================

        profile_manager = ProfileManager(
            "config/profile.yaml"
        )

        profile_manager.load_profile()

        candidate_skills = (
            profile_manager.get_all_skills()
        )

        target_roles = (
            profile_manager.get_target_roles()
        )

        # ==================================================
        # 6. Load search preferences
        # ==================================================

        preferred_locations = (
            search_config.get(
                "locations",
                []
            )
        )

        preferred_work_modes = (
            search_config.get(
                "work_modes",
                []
            )
        )

        experience_config = (
            search_config.get(
                "experience",
                {}
            )
        )

        candidate_min_experience = (
            experience_config.get(
                "minimum",
                0
            )
        )

        candidate_max_experience = (
            experience_config.get(
                "maximum",
                2
            )
        )

        # ==================================================
        # 7. Create JobEvaluator
        # ==================================================

        evaluator = JobEvaluator(
            candidate_skills=candidate_skills,
            target_roles=target_roles,
            preferred_locations=preferred_locations,
            preferred_work_modes=preferred_work_modes,
            candidate_min_experience=(
                candidate_min_experience
            ),
            candidate_max_experience=(
                candidate_max_experience
            )
        )

        # ==================================================
        # 8. Create repository and application components
        # ==================================================

        repository = JobRepository()

        application_tracker = ApplicationTracker(
            repository
        )

        review_queue = ReviewQueue(
            repository=repository,
            application_tracker=application_tracker
        )

        captcha_handler = CaptchaHandler()
        notifier = Notifier()

        application_workflow = ApplicationWorkflow(
            permission_manager=PermissionManager(),
            application_tracker=application_tracker,
            captcha_handler=captcha_handler,
            notifier=notifier
        )

        # ==================================================
        # 9. Create JobCollector
        # ==================================================

        collector = JobCollector(
            evaluator=evaluator,
            repository=repository
        )

        # ==================================================
        # 10. Process each job
        # ==================================================

        for index, job in enumerate(
            jobs_to_process,
            start=1
        ):

            print(
                "\n"
                + "=" * 60
            )

            print(
                f"JOB {index} OF "
                f"{len(jobs_to_process)}"
            )

            print(
                "=" * 60
            )

            print(
                "\nTitle:",
                job.get("title", "")
            )

            print(
                "Company:",
                job.get("company", "")
            )

            print(
                "Location:",
                job.get("location", "")
            )

            print(
                "Experience:",
                job.get("experience", "")
            )

            print(
                "URL:",
                job.get("job_url", "")
            )

            # ==================================================
            # 11. Extract complete job details
            # ==================================================

            print(
                "\nExtracting complete job details..."
            )

            job = browser.extract_job_details(
                job
            )

            print(
                "\n========== EXTRACTED JOB DESCRIPTION =========="
            )

            print(
                job.get(
                    "job_description",
                    ""
                )[:5000]
            )

            print(
                "========== END JOB DESCRIPTION =========="
            )

            # ==================================================
            # 12. Security challenge check
            # ==================================================

            if job.get(
                "security_challenge",
                False
            ):

                print(
                    "\nSecurity challenge detected."
                )

                print(
                    "Manual action is required."
                )

                print(
                    "Stopping pipeline."
                )

                return

            # ==================================================
            # 13. Make sure JD exists
            # ==================================================

            job_description = job.get(
                "job_description",
                ""
            )

            if not job_description:

                print(
                    "\nJob description is empty."
                )

                print(
                    "Skipping this job."
                )

                continue

            # ==================================================
            # 14. Send job to JobCollector
            # ==================================================

            print(
                "\nSending job to JobCollector..."
            )

            result = collector.process_job(
                job_description=job_description,
                job_url=job["job_url"],
                source="Naukri",
                job_metadata=job
            )

            # ==================================================
            # 15. Get evaluation
            # ==================================================

            evaluation = result[
                "evaluation"
            ]

            processed_job = result[
                "job"
            ]

            workflow_result = (
                application_workflow.process_job(
                    processed_job,
                    page_text=processed_job.get(
                        "job_description",
                        ""
                    )
                )
            )

            if (
                resume_tailoring
                and processed_job.get("match_score", 0)
                >= config_manager.get_minimum_score()
            ):
                try:
                    draft_path = resume_tailoring.create_draft(processed_job)
                except (OSError, RuntimeError, ValueError) as error:
                    print(
                        "\nResume draft failed for "
                        f"{processed_job.get('title', 'Unknown')} at "
                        f"{processed_job.get('company', 'Unknown')}: "
                        f"{type(error).__name__}: {error}"
                    )
                else:
                    print(f"\nTailored resume draft saved: {draft_path}")

            # ==================================================
            # 16. Display evaluation
            # ==================================================

            print(
                "\n---------- EVALUATION ----------"
            )

            print(
                "\nJob Title:"
            )

            print(
                processed_job["title"]
            )

            print(
                "\nCompany:"
            )

            print(
                processed_job["company"]
            )

            print(
                "\nRole Match:"
            )

            print(
                evaluation[
                    "role_match"
                ]
            )

            print(
                "\nSkill Match:"
            )

            print(
                evaluation[
                    "skill_match"
                ]
            )

            print(
                "\nExperience Match:"
            )

            print(
                evaluation[
                    "experience_match"
                ]
            )

            print(
                "\nLocation Match:"
            )

            print(
                evaluation[
                    "location_match"
                ]
            )

            print(
                "\nFinal Match Score:"
            )

            print(
                evaluation[
                    "final_score"
                ]
            )

            print(
                "\nScore Category:"
            )

            print(
                evaluation[
                    "score_category"
                ]
            )

            print(
                "\nApplication Status:"
            )

            print(
                workflow_result[
                    "status"
                ]
            )

            print(
                "\nInserted Into Database:"
            )

            print(
                result[
                    "inserted"
                ]
            )

            print(
                "\nUpdated in Database:"
            )

            print(
                result[
                    "updated"
                ]
            )

        # ==================================================
        # 17. Review pending jobs
        # ==================================================

        print(
            "\n========== STARTING REVIEW QUEUE =========="
        )

        if run_review:
            review_queue.review_jobs_interactively()
        else:
            print(
                "\nJobs remain in the review queue. No applications were "
                "submitted; review and apply manually."
            )

        # ==================================================
        # 18. Processing completed
        # ==================================================

        print(
            "\n"
            + "=" * 60
        )

        print(
            "20-JOB PIPELINE TEST COMPLETED"
        )

        print(
            "=" * 60
        )

    except Exception as error:

        print(
            "\n========== TEST FAILED =========="
        )

        print(
            type(error).__name__
        )

        print(
            error
        )

    finally:

        browser.close()

        print(
            "\nBrowser closed."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Search for matching jobs, update the profile resume, and "
            "create resume drafts."
        )
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--schedule",
        action="store_true",
        help="Run the pipeline daily at the configured local time.",
    )
    actions.add_argument(
        "--setup-naukri-session",
        action="store_true",
        help="Sign in manually and save a local Naukri browser session.",
    )
    arguments = parser.parse_args()

    if arguments.setup_naukri_session:
        config_manager = ConfigManager()
        profile_config = config_manager.get_naukri_profile_config()
        browser = NaukriBrowser(headless=False)
        try:
            browser.start_persistent(
                profile_config.get(
                    "browser_profile_directory",
                    "data/naukri_browser_profile",
                )
            )
            browser.setup_naukri_login()
            input(
                "Sign in to Naukri in the opened browser. "
                "After you reach your account, press Enter here to save "
                "the session: "
            )
            print("Local Naukri browser session is ready.")
        finally:
            browser.close()
    elif arguments.schedule:
        schedule_config = ConfigManager().get_schedule_config()
        if not schedule_config.get("enabled", False):
            raise RuntimeError("Daily scheduling is disabled in configuration.")
        run_daily(
            task=lambda: main(run_review=False),
            run_at=schedule_config.get("time", "09:30"),
            timezone_name=schedule_config.get(
                "timezone", "Asia/Kolkata"
            ),
        )
    else:
        main()