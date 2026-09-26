from src.matching.skill_matcher import SkillMatcher
from src.profile.profile_updater import ProfileManager


def main():

    print("\n========== SKILL MATCHER TEST ==========")

    # Load candidate skills from profile
    profile_manager = ProfileManager("config/profile.yaml")
    profile_manager.load_profile()

    candidate_skills = profile_manager.get_all_skills()

    print("\nCandidate skills:")
    print(candidate_skills)

    # Simulated skills extracted from a job description
    job_skills = [
        "Python",
        "SQL",
        "Power BI",
        "Tableau",
        "AWS",
        "Spark"
    ]

    # Create matcher
    matcher = SkillMatcher(candidate_skills)

    # Get matching result
    result = matcher.get_match_result(job_skills)

    print("\nJob skills:")
    print(job_skills)

    print("\nMatched skills:")
    print(result["matched_skills"])

    print("\nMissing skills:")
    print(result["missing_skills"])

    print("\nMatch percentage:")
    print(result["match_percentage"])

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()