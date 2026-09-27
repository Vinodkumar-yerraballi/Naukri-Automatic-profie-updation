from src.profile.profile_updater import ProfileManager
from src.matching.skill_matcher import SkillMatcher


def main():

    # Load candidate profile
    profile = ProfileManager("config/profile.yaml")
    profile.load_profile()

    candidate_skills = profile.get_all_skills()

    print("\n========== CANDIDATE SKILLS ==========")
    for skill in candidate_skills:
        print(f"✓ {skill}")

    print(f"\nTotal candidate skills: {len(candidate_skills)}")

    # Create matcher
    matcher = SkillMatcher(candidate_skills)

    # Simulated realistic Data Analyst job
    job_skills = [
        "Python",
        "SQL",
        "Pandas",
        "Power BI",
        "Tableau",
        "Excel",
        "Machine Learning",
        "Statistics",
        "AWS",
    ]

    print("\n========== JOB SKILLS ==========")

    for skill in job_skills:
        print(f"• {skill}")

    # Run matching
    result = matcher.get_match_result(job_skills)

    print("\n========== MATCH RESULT ==========")

    print("\nMatched Skills:")
    for skill in result["matched_skills"]:
        print(f"✓ {skill}")

    print("\nMissing Skills:")
    for skill in result["missing_skills"]:
        print(f"✗ {skill}")

    print(
        f"\nSkill Match Percentage: "
        f"{result['match_percentage']}%"
    )

    print("==================================")


if __name__ == "__main__":
    main()