from src.matching.experience_matcher import ExperienceMatcher
from src.utils.logger import setup_logger


logger = setup_logger()


def main():

    logger.info("Starting experience matching test")

    # Candidate's acceptable experience range
    matcher = ExperienceMatcher(
        candidate_min_experience=0,
        candidate_max_experience=2
    )

    test_jobs = [
        "0-2 years",
        "1-3 years",
        "3-5 years",
        "5+ years",
        "2 years",
        "1 year",
        "Experience not specified"
    ]

    print("\n========== EXPERIENCE MATCHING ==========")

    for experience in test_jobs:

        result = matcher.get_match_result(
            experience
        )

        print(
            f"\nJob Requirement: {experience}"
        )

        print(
            f"Parsed Range: "
            f"{result['job_min_experience']} - "
            f"{result['job_max_experience']}"
        )

        print(
            f"Match: {result['match']}"
        )

    logger.info(
        "Experience matching completed successfully"
    )


if __name__ == "__main__":
    main()