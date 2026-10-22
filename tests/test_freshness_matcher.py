
from src.matching.freshness_matcher import FreshnessMatcher


def main():
    matcher = FreshnessMatcher()

    test_cases = [
        "Just now",
        "Today",
        "5 hours ago",
        "1 day ago",
        "3 days ago",
        "6 days ago",
        "2 weeks ago",
        "1 month ago",
        "",
    ]

    for posted in test_cases:
        result = matcher.get_match_result(posted)
        print(f"Posted: {posted or 'Unknown'}")
        print(f"Result: {result}")
        print("-" * 50)


if __name__ == "__main__":
    main()
