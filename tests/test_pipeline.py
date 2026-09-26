from src.ingestion.job_collector import JobCollector
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.profile.profile_updater import ProfileManager
from src.application.application_workflow import ApplicationWorkflow
from src.pipelines.job_pipeline import JobPipeline
from src.application.permission import PermissionManager
from src.application.application_tracker import ApplicationTracker
from src.application.captcha_handler import CaptchaHandler
from src.notification.notifier import Notifier

def create_pipeline():

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

    job_collector = JobCollector(
        evaluator,
        repository
    )

    permission_manager = PermissionManager()
    application_tracker = ApplicationTracker(repository)
    captcha_handler = CaptchaHandler()
    notifier = Notifier()

    application_workflow = ApplicationWorkflow(
        permission_manager,
        application_tracker,
        captcha_handler,
        notifier
    )

    pipeline = JobPipeline(
        job_collector=job_collector,
        application_workflow=application_workflow
    )

    return pipeline


def main():

    print("\n========== PIPELINE TEST ==========")

    pipeline = create_pipeline()

    job_url = (
        "https://www.naukri.com/job-listings-pipeline-test-"
        "data-analyst-new-company-0-to-2-years-test888888"
    )

    job_description = """
    Data Analyst

    Pipeline Test Company is looking for a Data Analyst.

    Location: Remote

    Experience: 0-2 years

    Required Skills:
    Python, SQL, Power BI
    """

    
    print("\n========== FIRST RUN ==========")

    first_result = pipeline.process_job(
        job_description=job_description,
        job_url=job_url,
        source="TEST",
        page_text=job_description
    )

    print(f"Inserted: {first_result['inserted']}")
    print(f"Updated: {first_result['updated']}")

    print("\n========== SECOND RUN ==========")

    second_result = pipeline.process_job(
        job_description=job_description,
        job_url=job_url,
        source="TEST",
        page_text=job_description
    )

    print(f"Inserted: {second_result['inserted']}")
    print(f"Updated: {second_result['updated']}")

    print("\nJob after second run:")
    print(f"Title: {second_result['job']['title']}")
    print(f"Company: {second_result['job']['company']}")
    print(f"Location: {second_result['job']['location']}")
    print(f"Experience: {second_result['job']['experience']}")
    print(f"Match Score: {second_result['job']['match_score']}")
    print(f"Status: {second_result['job']['status']}")

    print("\nWorkflow:")
    print(second_result["workflow"])


if __name__ == "__main__":
    main()