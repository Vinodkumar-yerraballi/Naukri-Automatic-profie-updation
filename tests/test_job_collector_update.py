from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.ingestion.job_collector import JobCollector
from src.profile.profile_updater import ProfileManager


def create_collector():
    profile_manager = ProfileManager("config/profile.yaml")
    profile = profile_manager.load_profile()

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
    print("\n========== JOB COLLECTOR UPDATE TEST ==========")

    collector = create_collector()

    job_url = (
        "https://www.naukri.com/job-listings-data-analyst-"
        "berg-technologies-bengaluru-2-to-4-years-070426015264"
    )

    job_description = """
    Data Analyst

    Berg Technologies Private Limited is looking for a Data Analyst.

    Location: Remote

    Experience: 0-2 years

    Required Skills:
    Python, SQL, Power BI
    """

    result = collector.process_job(
        job_description=job_description,
        job_url=job_url,
        source="Naukri",
        job_metadata={
            "title": "Data Analyst - Collector Test",
            "company": "Berg Technologies Private Limited",
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