from src.ingestion.job_collector import JobCollector
from src.profile.profile_updater import ProfileManager
from src.config.config_manager import ConfigManager
from src.database.job_repository import JobRepository
from src.matching.job_evaluator import JobEvaluator


def main():

    print("\n========== JOB COLLECTOR SKILL TEST ==========")

    # --------------------------------------------------
    # 1. Load candidate profile
    # --------------------------------------------------

    profile_manager = ProfileManager("config/profile.yaml")
    profile_manager.load_profile()

    candidate_skills = profile_manager.get_all_skills()
    target_roles = profile_manager.get_target_roles()

    # --------------------------------------------------
    # 2. Load job preferences
    # --------------------------------------------------

    config_manager = ConfigManager()
    job_search_config = config_manager.get_job_search_config()

    preferred_locations = job_search_config.get("locations", [])
    preferred_work_modes = job_search_config.get("work_modes", [])

    experience_config = job_search_config.get("experience", {})

    candidate_min_experience = experience_config.get("minimum", 0)
    candidate_max_experience = experience_config.get("maximum", 2)

    # --------------------------------------------------
    # 3. Create JobEvaluator
    # --------------------------------------------------

    evaluator = JobEvaluator(
        candidate_skills=candidate_skills,
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        preferred_work_modes=preferred_work_modes,
        candidate_min_experience=candidate_min_experience,
        candidate_max_experience=candidate_max_experience
    )

    # --------------------------------------------------
    # 4. Create repository
    # --------------------------------------------------

    repository = JobRepository(
        database_path="data/job_automation.db"
    )

    # --------------------------------------------------
    # 5. Create JobCollector
    # --------------------------------------------------

    collector = JobCollector(
        evaluator=evaluator,
        repository=repository
    )

    # --------------------------------------------------
    # 6. Sample job description
    # --------------------------------------------------

    job_description = """
    Data Analyst

    ABC Technologies is looking for a Data Analyst.

    Location: Remote

    Experience: 0-2 years

    Required Skills:
    Python, SQL, Power BI, Tableau, AWS, Spark,
    Pandas, Machine Learning and Git.

    The candidate should have experience in
    statistical analysis and data visualization.
    """

    job_url = "https://example.com/test-job-collector-skills"

    # --------------------------------------------------
    # 7. Process job through JobCollector
    # --------------------------------------------------

    result = collector.process_job(
        job_description=job_description,
        job_url=job_url,
        source="TEST"
    )

    job = result["job"]
    evaluation = result["evaluation"]

    # --------------------------------------------------
    # 8. Display results
    # --------------------------------------------------

    print("\n========== COLLECTED JOB ==========")

    print("\nTitle:")
    print(job["title"])

    print("\nCompany:")
    print(job["company"])

    print("\nLocation:")
    print(job["location"])

    print("\nExperience:")
    print(job["experience"])

    print("\nExtracted Skills:")
    print(job["skills"])

    print("\nMatch Score:")
    print(job["match_score"])

    print("\nStatus:")
    print(job["status"])

    print("\n========== SKILL MATCH ==========")

    print("\nMatched Skills:")
    print(evaluation["skill_match"]["matched_skills"])

    print("\nMissing Skills:")
    print(evaluation["skill_match"]["missing_skills"])

    print("\nSkill Match Percentage:")
    print(evaluation["skill_match"]["match_percentage"])

    print("\n========== DATABASE RESULT ==========")

    print("\nInserted:")
    print(result["inserted"])

    print("\nUpdated:")
    print(result["updated"])

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()
