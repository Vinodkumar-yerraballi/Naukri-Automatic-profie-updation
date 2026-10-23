
from src.matching.freshness_matcher import FreshnessMatcher


def test_is_within_last_24_hours_accepts_recent_postings():
    matcher = FreshnessMatcher()

    assert matcher.is_within_last_hours("Just now")
    assert matcher.is_within_last_hours("Today")
    assert matcher.is_within_last_hours("5 hours ago")
    assert matcher.is_within_last_hours("1 day ago")


def test_is_within_last_24_hours_rejects_old_or_unknown_postings():
    matcher = FreshnessMatcher()

    assert not matcher.is_within_last_hours("25 hours ago")
    assert not matcher.is_within_last_hours("2 days ago")
    assert not matcher.is_within_last_hours("2 weeks ago")
    assert not matcher.is_within_last_hours("")
    assert not matcher.is_within_last_hours("Posting age unknown")


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
