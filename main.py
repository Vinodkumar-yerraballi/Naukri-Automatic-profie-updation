from src.extraction.jb_extractor import JDExtractor
from src.profile.profile_updater import ProfileManager
from src.utils.logger import setup_logger


logger = setup_logger()


def main():

    logger.info("Starting JD extraction test")

    # Load candidate profile
    profile_manager = ProfileManager(
        "config/profile.yaml"
    )

    profile_manager.load_profile()

    # Get candidate skills
    candidate_skills = profile_manager.get_all_skills()

    # Sample job description
    job_description = """
Data Analyst

ABC Technologies is looking for a Data Analyst.

Requirements:
- Python
- SQL
- Pandas
- Power BI
- Machine Learning
- Statistics

Experience:
0-2 years

Location:
Bangalore
"""

    # Create extractor
    extractor = JDExtractor(job_description)

    # Extract information
    job = extractor.extract_all(candidate_skills)

    print("\n========== JOB INFORMATION ==========")

    print("\nTitle:")
    print(job["title"])

    print("\nCompany:")
    print(job["company"])

    print("\nLocation:")
    print(job["location"])

    print("\nExperience:")
    print(job["experience"])

    print("\nSkills:")
    for skill in job["skills"]:
        print("-", skill)

    logger.info("JD extraction completed successfully")


if __name__ == "__main__":
    main()