from src.ingestion.naukri_browser import NaukriBrowser
from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.config.config_manager import ConfigManager
from src.profile.profile_updater import ProfileManager


def main():

    print("\n========== NAUKRI -> PIPELINE TEST ==========")

    browser = NaukriBrowser(
        headless=False
    )

    try:

        # ==================================================
        # 1. Start browser
        # ==================================================

        browser.start()

        # ==================================================
        # 2. Search Naukri
        # ==================================================

        browser.search_jobs(
            role="Data Analyst",
            location="Bangalore"
        )

        # ==================================================
        # 3. Get job cards
        # ==================================================

        jobs = browser.get_job_cards()

        print(f"\nJobs found: {len(jobs)}")

        if not jobs:
            print("No jobs found.")
            return

        # ==================================================
        # 4. Select first 5 jobs
        # ==================================================

        jobs_to_process = jobs[:3]

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

        config_manager = ConfigManager()

        search_config = (
            config_manager.get_job_search_config()
        )

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
        # 8. Create repository
        # ==================================================

        repository = JobRepository()

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
            print("\n========== EXTRACTED JOB DESCRIPTION ==========")
            print(job.get("job_description", "")[:5000])
            print("========== END JOB DESCRIPTION ==========")

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
                "\nJob Status:"
            )

            print(
                processed_job[
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
                "\nupdated in Database"
            )
            print(
                result["updated"]
            )

        # ==================================================
        # 17. Processing completed
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
    main()
