from src.matching.job_evaluator import JobEvaluator
from src.profile.profile_updater import ProfileManager
from src.config.config_manager import ConfigManager


def main():

    print("\n========== JOB EVALUATOR SKILL TEST ==========")

    # Load candidate profile
    profile_manager = ProfileManager("config/profile.yaml")
    profile_manager.load_profile()

    candidate_skills = profile_manager.get_all_skills()
    target_roles = profile_manager.get_target_roles()

    # Load job preferences
    config_manager = ConfigManager()
    job_search_config = config_manager.get_job_search_config()

    preferred_locations = job_search_config.get("locations", [])
    preferred_work_modes = job_search_config.get("work_modes", [])

    experience_config = job_search_config.get("experience", {})

    candidate_min_experience = experience_config.get("minimum", 0)
    candidate_max_experience = experience_config.get("maximum", 2)

    # Create evaluator
    evaluator = JobEvaluator(
        candidate_skills=candidate_skills,
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        preferred_work_modes=preferred_work_modes,
        candidate_min_experience=candidate_min_experience,
        candidate_max_experience=candidate_max_experience
    )

    # Test job
    job = {
        "title": "Data Analyst",
        "location": "Remote",
        "experience": "0-2 years",
        "skills": [
            "Python",
            "SQL",
            "Power BI",
            "Tableau",
            "AWS",
            "Spark"
        ]
    }

    # Evaluate job
    result = evaluator.evaluate(job)

    print("\nJob:")
    print(job)

    print("\nMatched skills:")
    print(result["skill_match"]["matched_skills"])

    print("\nMissing skills:")
    print(result["skill_match"]["missing_skills"])

    print("\nSkill match percentage:")
    print(result["skill_match"]["match_percentage"])

    print("\nRole match:")
    print(result["role_match"])

    print("\nExperience match:")
    print(result["experience_match"])

    print("\nLocation match:")
    print(result["location_match"])

    print("\nFinal score:")
    print(result["final_score"])

    print("\nScore category:")
    print(result["score_category"])

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()