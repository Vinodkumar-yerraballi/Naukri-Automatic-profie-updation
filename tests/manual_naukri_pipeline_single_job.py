from src.ingestion.naukri_browser import NaukriBrowser
from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.profile.profile_updater import ProfileManager
from src.config.config_manager import ConfigManager


print("\n========== NAUKRI SINGLE JOB PIPELINE TEST ==========")

config_manager = ConfigManager()

profile_manager = ProfileManager(
    "config/profile.yaml"
)

profile_manager.load_profile()

candidate_skills = profile_manager.get_all_skills()
target_roles = profile_manager.get_target_roles()

job_search_config = config_manager.get_job_search_config()

preferred_locations = job_search_config.get(
    "locations",
    []
)

preferred_work_modes = job_search_config.get(
    "work_modes",
    []
)

experience_config = job_search_config.get(
    "experience",
    {}
)

candidate_min_experience = experience_config.get(
    "minimum",
    0
)

candidate_max_experience = experience_config.get(
    "maximum",
    2
)


evaluator = JobEvaluator(
    candidate_skills=candidate_skills,
    target_roles=target_roles,
    preferred_locations=preferred_locations,
    preferred_work_modes=preferred_work_modes,
    candidate_min_experience=candidate_min_experience,
    candidate_max_experience=candidate_max_experience
)

repository = JobRepository()

collector = JobCollector(
    evaluator=evaluator,
    repository=repository
)

browser = NaukriBrowser()

try:

    browser.start()

    browser.search_jobs(
        role="Data Analyst",
        location="Remote"
    )

    jobs = browser.get_job_cards()

    print(f"\nJobs found: {len(jobs)}")

    if not jobs:
        print("No jobs found.")
    else:

        # Process only one job
        job = jobs[1]

        print("\n========== SELECTED JOB ==========")

        print(f"Title:      {job.get('title')}")
        print(f"Company:    {job.get('company')}")
        print(f"Location:   {job.get('location')}")
        print(f"Experience: {job.get('experience')}")
        print(f"URL:        {job.get('job_url')}")

        print("\n========== EXTRACTING DETAILS ==========")

        job = browser.extract_job_details(job)

        if job.get("security_challenge"):
            print("\nSecurity challenge detected.")
            print("Manual action is required.")

        else:

            job_description = job.get(
                "job_description",
                ""
            )

            print(
                f"\nJob description length: "
                f"{len(job_description)}"
            )

            if not job_description.strip():

                print(
                    "\nJob description is empty."
                )

            else:

                print(
                    "\n========== PROCESSING JOB =========="
                )

                result = collector.process_job(
                    job_description=job_description,
                    job_url=job.get("job_url"),
                    source="Naukri",
                    job_metadata=job
                )

                print(
                    "\n========== COLLECTOR RESULT =========="
                )

                print(
                    f"Inserted: "
                    f"{result['inserted']}"
                )

                print(
                    f"Updated: "
                    f"{result['updated']}"
                )

                print(
                    f"Match Score: "
                    f"{result['job']['match_score']}"
                )

                print(
                    f"Status: "
                    f"{result['job']['status']}"
                )

                evaluation = result["evaluation"]

                print(
                    "\nMatched Skills:"
                )

                print(
                    evaluation["skill_match"][
                        "matched_skills"
                    ]
                )

                print(
                    "\nMissing Skills:"
                )

                print(
                    evaluation["skill_match"][
                        "missing_skills"
                    ]
                )

                print(
                    "\nSkill Match Percentage:"
                )

                print(
                    evaluation["skill_match"][
                        "match_percentage"
                    ]
                )

                print(
                    "\nFinal Score:"
                )

                print(
                    evaluation["final_score"]
                )

                print(
                    "\nScore Category:"
                )

                print(
                    evaluation["score_category"]
                )

finally:

    browser.close()

print(
    "\n========== TEST COMPLETED =========="
)