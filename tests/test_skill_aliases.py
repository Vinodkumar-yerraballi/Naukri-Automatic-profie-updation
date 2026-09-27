from src.matching.skill_matcher import SkillMatcher


def main():

    candidate_skills = [
        "Statistical Analysis",
        "Power BI",
        "Machine Learning",
        "NumPy",
        "Data Wrangling",
        "NLP"
    ]

    job_skills = [
        "Statistics",
        "PowerBI",
        "ML",
        "Numpy",
        "Data Cleaning",
        "Natural Language Processing"
    ]

    matcher = SkillMatcher(candidate_skills)

    result = matcher.get_match_result(job_skills)

    print("\n========== ALIAS TEST ==========")

    print("\nCandidate Skills:")
    for skill in candidate_skills:
        print(f"✓ {skill}")

    print("\nJob Skills:")
    for skill in job_skills:
        print(f"• {skill}")

    print("\nMatched Skills:")
    for skill in result["matched_skills"]:
        print(f"✓ {skill}")

    print("\nMissing Skills:")
    for skill in result["missing_skills"]:
        print(f"✗ {skill}")

    print(
        f"\nMatch Percentage: "
        f"{result['match_percentage']}%"
    )

    print("================================")


if __name__ == "__main__":
    main()