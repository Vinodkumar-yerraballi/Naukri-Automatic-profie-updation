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

    config_manager = ConfigManager()

    profile_manager = ProfileManager(
        "config/profile.yaml"
    )

    candidate_skills = profile_manager.get_all_skills()

    target_roles = profile_manager.get_target_roles()

    job_search_config = (
        config_manager.get_job_search_config()
    )

    preferred_locations = job_search_config.get(
        "locations",
        []
    )

    preferred_work_modes = job_search_config.get(
        "work_modes",
        []
    )

    evaluator = JobEvaluator(
        candidate_skills=candidate_skills,
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        preferred_work_modes=preferred_work_modes
    )

    repository = JobRepository(
        "data/test_job_pipeline.db"
    )

    job_collector = JobCollector(
        evaluator=evaluator,
        repository=repository
    )

    permission_manager = PermissionManager()

    application_tracker = ApplicationTracker(
        repository
    )

    captcha_handler = CaptchaHandler()

    notifier = Notifier()

    application_workflow = ApplicationWorkflow(
        permission_manager=permission_manager,
        application_tracker=application_tracker,
        captcha_handler=captcha_handler,
        notifier=notifier
    )

    pipeline = JobPipeline(
        job_collector=job_collector,
        application_workflow=application_workflow
    )


    job_metadata={
    "title": "Data Analyst",
    "company": "ABC Technologies",
    "location": "Bangalore",
    "experience": "0-2 years",
    "employment_type": "Full Time",
    "education": ["M.Sc."]
    }
    
    job_description = """
    Job Description

    Data Analyst

    ABC Technologies is looking for a Data Analyst.

    Location: Bangalore

    Experience: 0-2 years

    Key Skills:
    Python, SQL, Pandas, Power BI, Statistics

    Responsibilities:
    Analyze business data and create dashboards.
    Perform data analysis and reporting.
    """

    result = pipeline.process_job(
        job_description=job_description,
        job_url="https://test.com/pipeline-job-001",
        source="Naukri",
        page_text=job_description,
        job_metadata=job_metadata
    )

    print("\n========== PIPELINE RESULT ==========")

    print("Title:", result["job"]["title"])
    print("Company:", result["job"]["company"])
    print("Location:", result["job"]["location"])
    print("Skills:", result["job"]["skills"])
    print("Match Score:", result["job"]["match_score"])
    print("Status:", result["workflow"]["status"])
    print("Inserted:", result["inserted"])
    print("Updated:", result["updated"])

    print("\nEvaluation:")
    print(result["evaluation"])

    print("\nWorkflow:")
    print(result["workflow"])


if __name__ == "__main__":
    main()