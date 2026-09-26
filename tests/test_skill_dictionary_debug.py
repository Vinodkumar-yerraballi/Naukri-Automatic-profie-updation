from src.extraction.skill_dictionary import JOB_SKILLS


def main():
    job_description = """
    project managementdata analyticsoracledata analysisdata management
    data warehousingbusiness analysisdata collectionbusiness intelligence
    master data managementsqldata cleansingexceldata qualitytableausparkdata governance
    """

    jd_lower = job_description.lower()

    print("\n========== SKILL DICTIONARY DEBUG ==========")

    for skill in JOB_SKILLS:
        skill_lower = skill.lower().strip()

        if skill_lower in jd_lower:
            print(f"FOUND    : {skill}")
        else:
            print(f"NOT FOUND: {skill}")

    print("============================================")


if __name__ == "__main__":
    main()