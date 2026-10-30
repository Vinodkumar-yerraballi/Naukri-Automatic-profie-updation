import argparse
from datetime import date

from playwright.sync_api import Error as PlaywrightError

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
from src.profile.platform_resume_uploader import (
    CandidatePlatformBrowser,
    PlatformProfileUpdater,
    PlatformResumeUploader,
)
from src.profile.resume_profile_proposal import ResumeProfileProposal
from src.pipelines.daily_scheduler import run_daily
from src.matching.freshness_matcher import FreshnessMatcher


def _select_search_queries(
    roles: list[str],
    locations: list[str],
    max_searches: int,
    day_offset: int,
) -> list[tuple[str, str]]:
    """Prioritize searching every role, then expand location coverage."""
    selected_queries = []
    selected_set = set()

    for location_round in range(len(locations)):
        for role_index, role in enumerate(roles):
            location_index = (
                day_offset + role_index + location_round
            ) % len(locations)
            query = (role, locations[location_index])
            if query not in selected_set:
                selected_queries.append(query)
                selected_set.add(query)
            if len(selected_queries) >= max_searches:
                return selected_queries

    return selected_queries


def update_candidate_platform(
    platform: str,
    platform_config: dict,
    resume_path: str,
    resume_tailoring,
    playwright=None,
) -> list[str]:
    """Update one platform's resume and configured resume-supported fields."""
    browser = CandidatePlatformBrowser(platform)
    failures = []
    try:
        browser.start_persistent(
            platform_config.get(
                "browser_profile_directory",
                f"data/{platform}_browser_profile",
            ),
            playwright=playwright,
        )
    except (
        OSError,
        PlaywrightError,
        RuntimeError,
        ValueError,
    ) as error:
        browser.close()
        return [
            f"{platform.title()} browser could not be started: "
            f"{type(error).__name__}: {error}"
        ]

    try:
        platform_resume = platform_config.get("resume_path", resume_path)
        if platform_config.get("update_resume", False):
            try:
                uploader = PlatformResumeUploader(
                    platform,
                    platform_config.get(
                        "upload_state_file",
                        f"data/{platform}_resume_upload.json",
                    ),
                )
                if uploader.update_if_changed(browser, platform_resume):
                    print(
                        f"{platform.title()} profile resume updated from: "
                        f"{platform_resume}"
                    )
            except (
                OSError,
                PlaywrightError,
                RuntimeError,
                ValueError,
            ) as error:
                failures.append(
                    f"{platform.title()} resume upload failed: "
                    f"{type(error).__name__}: {error}"
                )

        if platform_config.get("update_profile_fields", False):
            try:
                profile_updater = PlatformProfileUpdater(
                    platform,
                    platform_config.get(
                        "profile_update_state_file",
                        f"data/{platform}_profile_update.json",
                    ),
                )
                reconcile_foundit = platform == "foundit"
                if (
                    not profile_updater.is_current(platform_resume)
                    or reconcile_foundit
                ):
                    if not resume_tailoring:
                        raise RuntimeError(
                            "Resume tailoring is required to extract profile "
                            "fields from the source resume."
                        )
                    proposal_builder = ResumeProfileProposal(
                        resume_tailoring
                    )
                    proposal = proposal_builder.create(
                        platform_config.get(
                            "profile_update_sections",
                            ["skills", "employment", "projects"],
                        ),
                        review_required=False,
                    )
                    updated_fields = profile_updater.update_if_changed(
                        browser,
                        platform_resume,
                        proposal,
                        force=reconcile_foundit,
                    )
                    if updated_fields:
                        print(
                            f"{platform.title()} profile fields updated "
                            "from the resume: "
                            f"{', '.join(updated_fields)}"
                        )
                    else:
                        print(
                            f"{platform.title()} profile fields already "
                            "match resume-supported records; existing "
                            "records were preserved."
                        )
            except (
                OSError,
                PlaywrightError,
                RuntimeError,
                ValueError,
            ) as error:
                failures.append(
                    f"{platform.title()} profile-field update failed: "
                    f"{type(error).__name__}: {error}"
                )
    finally:
        browser.close()
    return failures


def update_naukri_candidate_profile(
    browser: NaukriBrowser,
    profile_config: dict,
    resume_path: str,
    resume_tailoring,
    reconcile_profile_fields: bool = False,
) -> list[str]:
    """Upload a changed Naukri resume and update supported profile fields."""
    failures = []
    if profile_config.get("update_resume", False):
        try:
            uploader = NaukriResumeUploader(
                profile_config.get(
                    "upload_state_file",
                    "data/profile_resume_upload.json",
                )
            )
            if uploader.update_if_changed(browser, resume_path):
                print(f"Naukri profile resume updated from: {resume_path}")
        except (
            OSError,
            PlaywrightError,
            RuntimeError,
            ValueError,
        ) as error:
            failures.append(
                "Naukri resume upload failed: "
                f"{type(error).__name__}: {error}"
            )

    if profile_config.get("update_profile_fields", False):
        try:
            profile_updater = PlatformProfileUpdater(
                "naukri",
                profile_config.get(
                    "profile_update_state_file",
                    "data/naukri_profile_update.json",
                ),
            )
            if (
                not profile_updater.is_current(resume_path)
                or reconcile_profile_fields
            ):
                if not resume_tailoring:
                    raise RuntimeError(
                        "Resume tailoring is required to extract Naukri "
                        "profile fields."
                    )
                proposal = ResumeProfileProposal(resume_tailoring).create(
                    profile_config.get(
                        "profile_update_sections",
                        ["headline", "skills", "projects"],
                    ),
                    review_required=False,
                )
                updated_fields = profile_updater.update_if_changed(
                    browser,
                    resume_path,
                    proposal,
                    force=reconcile_profile_fields,
                )
                if updated_fields:
                    print(
                        "Naukri profile fields updated from the resume: "
                        f"{', '.join(updated_fields)}"
                    )
                else:
                    print(
                        "Naukri profile fields already match the "
                        "resume-supported details."
                    )
        except (
            OSError,
            PlaywrightError,
            RuntimeError,
            ValueError,
        ) as error:
            failures.append(
                "Naukri profile-field update failed: "
                f"{type(error).__name__}: {error}"
            )
    return failures


def main(run_review=True):

    print("\n========== NAUKRI JOB PIPELINE ==========")

    config_manager = ConfigManager()
    profile_config = config_manager.get_naukri_profile_config()
    resume_config = config_manager.get_resume_tailoring_config()
    profile_update_enabled = profile_config.get("update_resume", False)
    naukri_profile_fields_enabled = profile_config.get(
        "update_profile_fields",
        False,
    )
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

        if profile_update_enabled or naukri_profile_fields_enabled:
            browser.start_persistent(
                profile_config.get(
                    "browser_profile_directory",
                    "data/naukri_browser_profile",
                )
            )
            for failure in update_naukri_candidate_profile(
                browser,
                profile_config,
                source_resume,
                resume_tailoring,
            ):
                print(f"\n{failure}")
        else:
            browser.start()

        for platform, platform_config in (
            config_manager.get_resume_platform_configs().items()
        ):
            if not (
                platform_config.get("update_resume", False)
                or platform_config.get("update_profile_fields", False)
            ):
                continue
            failures = update_candidate_platform(
                platform,
                platform_config,
                source_resume,
                resume_tailoring,
                playwright=browser.playwright,
            )
            for failure in failures:
                print(
                    f"\n{failure}"
                )

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

        max_searches = max(
            1,
            int(
                search_config.get(
                    "max_searches_per_run",
                    len(roles) * len(locations),
                )
            ),
        )
        selected_queries = _select_search_queries(
            roles=roles,
            locations=locations,
            max_searches=max_searches,
            day_offset=date.today().toordinal(),
        )

        # Search every configured role first, then rotate through additional
        # locations while keeping the daily search count bounded.
        jobs_by_url = {}
        posted_within_hours = int(
            search_config.get("posted_within_hours", 24)
        )
        experience = search_config.get("experience")
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
                experience=experience,
            )
            if browser.detect_access_denied():
                print(
                    "Naukri denied access to the search page. Stopping "
                    "without retrying or attempting to bypass the denial."
                )
                return
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
            ),
            candidate_education=profile_manager.get_education()
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

        resume_drafts = {}

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

            description_quality_issues = job.get(
                "description_quality_issues",
                [],
            )
            if description_quality_issues:
                print(
                    "\nSkipping job because the extracted description "
                    "contains page-interface text:"
                )
                for issue in description_quality_issues:
                    print(f"- {issue}")
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
                    resume_drafts[processed_job["job_url"]] = str(draft_path)

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
            application_config = config_manager.get_application_config()
            submission_callback = None
            if application_config.get("auto_apply", False):
                maximum_applications = int(
                    application_config.get(
                        "maximum_applications_per_day", 15
                    )
                )

                def submit_approved_job(job):
                    attempts_today = (
                        repository.get_application_attempt_count_today()
                    )
                    if attempts_today >= maximum_applications:
                        return {
                            "status": "LIMIT_REACHED",
                            "message": (
                                "The configured daily application limit "
                                f"({maximum_applications}) has been reached."
                            ),
                        }

                    result = browser.submit_application(job)
                    if result["status"] == "APPLIED":
                        application_tracker.mark_applied(job["job_url"])
                        notifier.notify_application_status(
                            job.get("title", "Unknown"),
                            job.get("company", "Unknown"),
                            "APPLIED",
                        )
                    elif result["status"] == "ALREADY_APPLIED":
                        application_tracker.mark_already_applied(
                            job["job_url"]
                        )
                    elif result["status"] == "UNCONFIRMED":
                        application_tracker.mark_application_unconfirmed(
                            job["job_url"]
                        )
                    return result

                submission_callback = submit_approved_job

            review_queue.review_jobs_interactively(
                submission_callback=submission_callback,
                resume_drafts=resume_drafts,
            )
        else:
            print(
                "\nJobs remain in the review queue. No applications were "
                "submitted because interactive approval was not enabled."
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
    actions.add_argument(
        "--setup-foundit-session",
        action="store_true",
        help="Sign in manually and save a local Foundit browser session.",
    )
    actions.add_argument(
        "--setup-indeed-session",
        action="store_true",
        help="Sign in manually and save a local Indeed browser session.",
    )
    actions.add_argument(
        "--update-foundit-profile",
        action="store_true",
        help=(
            "Update Foundit resume, skills, experience, and projects without "
            "running the Naukri job search."
        ),
    )
    actions.add_argument(
        "--update-all-profiles",
        action="store_true",
        help=(
            "Update configured Naukri and Foundit profiles once without "
            "running the job search."
        ),
    )
    actions.add_argument(
        "--update-naukri-profile",
        action="store_true",
        help=(
            "Update Naukri resume, headline, skills, and projects without "
            "running the job search."
        ),
    )
    actions.add_argument(
        "--prepare-profile-update",
        action="store_true",
        help=(
            "Create a reviewable profile-field proposal from data/resume.pdf "
            "without changing profile fields."
        ),
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
    elif arguments.setup_foundit_session or arguments.setup_indeed_session:
        platform = (
            "foundit"
            if arguments.setup_foundit_session
            else "indeed"
        )
        platform_config = ConfigManager().get_resume_platform_configs()[
            platform
        ]
        browser = CandidatePlatformBrowser(platform, headless=False)
        try:
            browser.start_persistent(
                platform_config.get(
                    "browser_profile_directory",
                    f"data/{platform}_browser_profile",
                )
            )
            browser.setup_login()
            input(
                f"Sign in to {platform.title()} in the opened browser. "
                "After you reach your account, press Enter here to save "
                "the session: "
            )
            print(f"Local {platform.title()} browser session is ready.")
        finally:
            browser.close()
    elif arguments.update_all_profiles:
        config_manager = ConfigManager()
        tailoring_config = config_manager.get_resume_tailoring_config()
        profile_config = config_manager.get_naukri_profile_config()
        naukri_resume = profile_config.get("resume_path", "data/resume.pdf")
        naukri_tailoring_config = dict(tailoring_config)
        naukri_tailoring_config["resume_path"] = naukri_resume
        naukri_tailoring = ResumeTailoringService.from_config(
            naukri_tailoring_config
        )
        browser = NaukriBrowser(headless=False)
        failures = []
        try:
            browser.start_persistent(
                profile_config.get(
                    "browser_profile_directory",
                    "data/naukri_browser_profile",
                )
            )
            failures.extend(
                update_naukri_candidate_profile(
                    browser,
                    profile_config,
                    naukri_resume,
                    naukri_tailoring,
                    reconcile_profile_fields=True,
                )
            )
        finally:
            browser.close()

        foundit_config = config_manager.get_resume_platform_configs()[
            "foundit"
        ]
        foundit_resume = foundit_config.get(
            "resume_path",
            "data/resume.pdf",
        )
        foundit_tailoring_config = dict(tailoring_config)
        foundit_tailoring_config["resume_path"] = foundit_resume
        foundit_tailoring = ResumeTailoringService.from_config(
            foundit_tailoring_config
        )
        failures.extend(
            update_candidate_platform(
                "foundit",
                foundit_config,
                foundit_resume,
                foundit_tailoring,
            )
        )
        if failures:
            raise RuntimeError("; ".join(failures))
    elif arguments.update_foundit_profile:
        config_manager = ConfigManager()
        platform_config = config_manager.get_resume_platform_configs()[
            "foundit"
        ]
        resume_path = platform_config.get("resume_path", "data/resume.pdf")
        resume_config = config_manager.get_resume_tailoring_config()
        resume_config["resume_path"] = resume_path
        resume_tailoring = ResumeTailoringService.from_config(resume_config)
        if not resume_tailoring:
            raise RuntimeError(
                "Resume tailoring must be enabled to extract Foundit "
                "profile fields."
            )
        failures = update_candidate_platform(
            "foundit",
            platform_config,
            resume_path,
            resume_tailoring,
        )
        if failures:
            raise RuntimeError("; ".join(failures))
    elif arguments.update_naukri_profile:
        config_manager = ConfigManager()
        profile_config = config_manager.get_naukri_profile_config()
        resume_path = profile_config.get("resume_path", "data/resume.pdf")
        resume_config = config_manager.get_resume_tailoring_config()
        resume_config["resume_path"] = resume_path
        resume_tailoring = ResumeTailoringService.from_config(resume_config)
        browser = NaukriBrowser(headless=False)
        try:
            browser.start_persistent(
                profile_config.get(
                    "browser_profile_directory",
                    "data/naukri_browser_profile",
                )
            )
            failures = update_naukri_candidate_profile(
                browser,
                profile_config,
                resume_path,
                resume_tailoring,
            )
            if failures:
                raise RuntimeError("; ".join(failures))
        finally:
            browser.close()
    elif arguments.prepare_profile_update:
        config_manager = ConfigManager()
        profile_config = config_manager.get_naukri_profile_config()
        resume_config = config_manager.get_resume_tailoring_config()
        resume_config["resume_path"] = profile_config.get(
            "resume_path",
            resume_config.get("resume_path", "data/resume.pdf"),
        )
        resume_tailoring = ResumeTailoringService.from_config(resume_config)
        if not resume_tailoring:
            raise RuntimeError(
                "Resume tailoring must be enabled to prepare profile updates."
            )
        proposal_builder = ResumeProfileProposal(resume_tailoring)
        proposal = proposal_builder.create(
            profile_config.get(
                "profile_update_sections",
                [
                    "headline",
                    "summary",
                    "skills",
                    "employment",
                    "education",
                    "projects",
                    "certifications",
                ],
            )
        )
        proposal_path = proposal_builder.save(
            proposal,
            profile_config.get(
                "profile_proposal_file",
                "data/processed/profile_update_proposal.json",
            ),
        )
        print(
            f"Profile update proposal saved for review: {proposal_path}\n"
            "No headline, skills, work history, education, project, or "
            "certification fields were changed on Naukri."
        )
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