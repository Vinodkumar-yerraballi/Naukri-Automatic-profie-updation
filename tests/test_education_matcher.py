
from src.matching.education_matcher import EducationMatcher


def main():
    matcher = EducationMatcher(
        candidate_education=["M.Sc. Applied Mathematics"]
    )

    test_cases = [
        (["M.Sc. Applied Mathematics"], 100.0),
        (["Master of Science"], 100.0),
        (["MBA"], 0.0),
        ([], None),
    ]

    for requirements, expected_score in test_cases:
        result = matcher.get_match_result(requirements)
        actual_score = result["score"]

        print("Requirements:", requirements)
        print("Result:", result)
        print("Expected score:", expected_score)
        print("Actual score:", actual_score)
        print("-" * 50)

        assert actual_score == expected_score

    print("All education matcher tests passed.")


if __name__ == "__main__":
    main()
