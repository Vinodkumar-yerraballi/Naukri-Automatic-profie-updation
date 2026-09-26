from src.matching.skill_matcher import SkillMatcher

def main():
    print("\n========== EMPTY SKILL TEST ==========")

    candidate_skills = [
        "Python",
        "SQL",
        "Power BI"
    ]
    matcher= SkillMatcher(candidate_skills)
    job_skills=[]
    result=matcher.get_match_result(job_skills)
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