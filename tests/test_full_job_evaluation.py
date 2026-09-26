from src.extraction.jd_extractor import JDExtractor
from src.matching.job_evaluator import JobEvaluator
from src.profile.profile_updater import ProfileManager
from src.config.config_manager import ConfigManager


def main():

    print("\n========== FULL JOB EVALUATION TEST ==========")

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
    # 3. Create evaluator
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
    # 4. Sample job description
    # --------------------------------------------------

    job_description = """
    Data Analyst

    ABC Technologies is looking for a Data Analyst.

    Location: Remote

    Experience: 0-2 years

    Required Skills:
    Python, SQL, Power BI, Tableau, AWS, Spark,
    Pandas, Machine Learning and Git.

    The candidate should have experience in data
    analysis and statistical analysis.
    """

    # --------------------------------------------------
    # 5. Extract job information
    # --------------------------------------------------

    extractor = JDExtractor(job_description)

    job = extractor.extract_all()

    print("\n========== EXTRACTED JOB ==========")

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

    # --------------------------------------------------
    # 6. Evaluate job
    # --------------------------------------------------

    evaluation = evaluator.evaluate(job)

    print("\n========== EVALUATION ==========")

    print("\nMatched Skills:")
    print(evaluation["skill_match"]["matched_skills"])

    print("\nMissing Skills:")
    print(evaluation["skill_match"]["missing_skills"])

    print("\nSkill Match Percentage:")
    print(evaluation["skill_match"]["match_percentage"])

    print("\nRole Match:")
    print(evaluation["role_match"])

    print("\nExperience Match:")
    print(evaluation["experience_match"])

    print("\nLocation Match:")
    print(evaluation["location_match"])

    print("\nFinal Score:")
    print(evaluation["final_score"])

    print("\nScore Category:")
    print(evaluation["score_category"])

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()