from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.profile.profile_updater import ProfileManager


def create_collector():

    profile_manager = ProfileManager("config/profile.yaml")
    profile_manager.load_profile()

    evaluator = JobEvaluator(
        candidate_skills=profile_manager.get_all_skills(),
        target_roles=profile_manager.get_target_roles(),
        preferred_locations=["Remote", "Bangalore", "Hyderabad", "Chennai"],
        preferred_work_modes=["Remote", "Hybrid"],
        candidate_min_experience=0,
        candidate_max_experience=2
    )

    repository = JobRepository()

    return JobCollector(evaluator, repository)


def main():

    print("\n========== JOB COLLECTOR INSERT TEST ==========")

    collector = create_collector()

    # New URL that should not already exist in the database
    job_url = (
        "https://www.naukri.com/job-listings-test-data-analyst-"
        "new-company-bengaluru-0-to-2-years-test999999"
    )

    job_description = """
    Data Analyst

    New Company is looking for a Data Analyst.

    Location: Remote

    Experience: 0-2 years

    Required Skills:
    Python, SQL, Power BI
    """

    result = collector.process_job(
        job_description=job_description,
        job_url=job_url,
        source="TEST",
        job_metadata={
            "title": "Test Data Analyst",
            "company": "New Company",
            "location": "Remote",
            "experience": "0-2 Yrs"
        }
    )

    print(f"Inserted: {result['inserted']}")
    print(f"Updated: {result['updated']}")

    print("\nJob after processing:")
    print(f"Title: {result['job']['title']}")
    print(f"Company: {result['job']['company']}")
    print(f"Location: {result['job']['location']}")
    print(f"Experience: {result['job']['experience']}")
    print(f"Match Score: {result['job']['match_score']}")
    print(f"Status: {result['job']['status']}")

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()