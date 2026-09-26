from src.extraction.jd_extractor import JDExtractor


def main():

    print("\n========== SKILL EXTRACTION TEST ==========")

    job_description = """
    We are looking for a Data Analyst.

    Required Skills:
    Python, SQL, Power BI, Tableau, Pandas, NumPy,
    Machine Learning, Statistics, Scikit-learn,
    Git and GitHub.

    Experience: 0-2 years
    """

    extractor = JDExtractor(job_description)

    skills = extractor.extract_skills()

    print("\nExtracted skills:")

    for skill in skills:
        print(f"- {skill}")

    print(f"\nTotal skills found: {len(skills)}")

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()