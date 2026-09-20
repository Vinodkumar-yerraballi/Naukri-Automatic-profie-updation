from src.profile.profile_updater import ProfileManager
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.ingestion.job_collector import JobCollector

from src.application.permission import PermissionManager
from src.application.application_tracker import ApplicationTracker
from src.application.captcha_handler import CaptchaHandler
from src.notification.notifier import Notifier
from src.application.application_workflow import ApplicationWorkflow

from src.pipelines.job_pipeline import JobPipeline


def main():

    print("\n========== JOB PIPELINE CONFIG TEST ==========")

    # 1. Load profile

    profile_manager = ProfileManager(
        "config/profile.yaml"
    )

    candidate_skills = (
        profile_manager.get_all_skills()
    )

    target_roles = (
        profile_manager.get_target_roles()
    )

    # 2. Candidate preferences

    preferred_locations = [
        "Remote",
        "Bangalore",
        "Hyderabad",
        "Chennai"
    ]

    preferred_work_modes = [
        "Remote",
        "Hybrid"
    ]

    # 3. Job evaluator

    evaluator = JobEvaluator(
        candidate_skills=candidate_skills,
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        preferred_work_modes=preferred_work_modes,
        candidate_min_experience=0,
        candidate_max_experience=2
    )

    # 4. Repository

    repository = JobRepository(
        "data/job_automation.db"
    )

    # 5. Job collector

    job_collector = JobCollector(
        evaluator=evaluator,
        repository=repository
    )

    # 6. Application components

    permission_manager = PermissionManager()

    tracker = ApplicationTracker(
        repository
    )

    captcha_handler = CaptchaHandler()

    notifier = Notifier()

    # 7. Application workflow

    application_workflow = ApplicationWorkflow(
        permission_manager=permission_manager,
        application_tracker=tracker,
        captcha_handler=captcha_handler,
        notifier=notifier
    )

    # 8. Pipeline

    pipeline = JobPipeline(
        job_collector=job_collector,
        application_workflow=application_workflow
    )

    # 9. Test job

    job_description = """
    Data Analyst

    ABC Technologies is looking for a Data Analyst.

    Location: Bangalore - Hybrid

    Experience: 0-2 years

    Skills:
    Python
    SQL
    Pandas
    NumPy
    Machine Learning
    Power BI
    NLP
    NLTK
    TF-IDF
    Sentiment Analysis
    Git
    GitHub
    """

    job_url = (
        "https://example.com/jobs/"
        "config-test-001"
    )

    # 10. Run pipeline

    result = pipeline.process_job(
        job_description=job_description,
        job_url=job_url,
        source="TEST",
        page_text="Normal job application page"
    )

    # 11. Display result

    print("\n========== PIPELINE RESULT ==========")

    print("\nMatch Score:")
    print(result["job"]["match_score"])

    print("\nJob Status:")
    print(result["job"]["status"])

    print("\nInserted:")
    print(result["inserted"])

    print("\nWorkflow Status:")
    print(result["workflow"]["status"])

    print("\nWorkflow Result:")
    print(result["workflow"])


if __name__ == "__main__":
    main()