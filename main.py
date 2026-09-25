from src.ingestion.naukri_browser import NaukriBrowser
from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.config.config_manager import ConfigManager
from src.profile.profile_updater import ProfileManager


def main():

    print(
        "\n========== NAUKRI → PIPELINE TEST =========="
    )

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

        print(
            f"\nJobs found: {len(jobs)}"
        )

        if not jobs:

            print(
                "No jobs found."
            )

            return

        # ==================================================
        # 4. Select ONE job
        # ==================================================

        job = jobs[0]

        print(
            "\n========== SELECTED JOB =========="
        )

        print("Title:", job["title"])
        print("Company:", job["company"])
        print("Location:", job["location"])
        print("Experience:", job["experience"])
        print("URL:", job["job_url"])

        # ==================================================
        # 5. Extract complete job details
        # ==================================================

        print(
            "\nExtracting complete job details..."
        )

        job = browser.extract_job_details(
            job
        )

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

            return

        # ==================================================
        # 6. Make sure JD exists
        # ==================================================

        job_description = job.get(
            "job_description",
            ""
        )

        if not job_description:

            print(
                "\nJob description is empty."
            )

            return

        # ==================================================
        # 7. Load candidate profile
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
        # 8. Load search preferences
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
        # 9. Create JobEvaluator
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
        # 10. Create repository
        # ==================================================

        repository = JobRepository()

        # ==================================================
        # 11. Create JobCollector
        # ==================================================

        collector = JobCollector(

            evaluator=evaluator,

            repository=repository
        )

        # ==================================================
        # 12. Send REAL Naukri JD
        #     into JobCollector
        # ==================================================

        print(
            "\nSending job to JobCollector..."
        )

        result = collector.process_job(

            job_description=job_description,

            job_url=job["job_url"],

            source="Naukri"
        )

        # ==================================================
        # 13. Display evaluation
        # ==================================================

        evaluation = result[
            "evaluation"
        ]

        processed_job = result[
            "job"
        ]

        print(
            "\n========== EVALUATION =========="
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