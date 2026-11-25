
import re


class FreshnessMatcher:
    """Score jobs according to how recently they were posted."""

    def is_within_last_hours(
        self,
        posted: str,
        max_hours: int = 5
    ) -> bool:
        """Return whether the displayed posting age is within the limit.

        Default is 5 hours for fresh job filtering. Pass a different value
        if you want a wider window.
        """
        return self.best_window(posted, [max_hours]) is not None

    @staticmethod
    def age_hours(posted: str) -> int | None:
        """Return the posting age in hours, or None when unknown."""
        if not posted:
            return None
        text = posted.lower().strip()
        if any(label in text for label in ("just now", "today", "few hours")):
            return 0
        match = re.search(
            r"(\d+)\+?\s*(hours?|hrs?|days?|weeks?|months?)",
            text
        )
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in ("hour", "hours", "hr", "hrs"):
            return amount
        if unit in ("day", "days"):
            return amount * 24
        return None

    @classmethod
    def best_window(
        cls,
        posted: str,
        windows: list[int],
    ) -> int | None:
        """Return the smallest freshness window (in hours) that the posting
        age fits, or None when it does not fit any window or is unknown.

        Windows are sorted ascending, so a job posted 3 hours ago matches the
        6-hour window rather than the 24-hour one.
        """
        if not posted or not windows:
            return None
        age = cls.age_hours(posted)
        if age is None:
            return None
        for window in sorted(set(int(w) for w in windows if int(w) > 0)):
            if age <= window:
                return window
        return None

    def get_match_result(self, posted: str) -> dict:
        if not posted or not posted.strip():
            return {
                "posted": posted,
                "score": None,
                "message": "Posting age is unavailable."
            }

        text = posted.lower().strip()

        if "just now" in text or "today" in text or "few hours" in text:
            score = 100.0
        else:
            match = re.search(r"(\d+)\+?\s*(hours?|hrs?|days?|weeks?|months?)", text)

            if not match:
                return {
                    "posted": posted,
                    "score": None,
                    "message": "Could not determine posting age."
                }

            amount = int(match.group(1))
            unit = match.group(2)

            if unit in ("hour", "hours", "hr", "hrs"):
                score = 100.0
            elif unit in ("day", "days"):
                score = 100.0 if amount <= 1 else 80.0 if amount <= 3 else 60.0 if amount <= 7 else 30.0
            elif unit in ("week", "weeks"):
                score = 30.0 if amount <= 2 else 10.0
            else:
                score = 0.0

        return {
            "posted": posted,
            "score": score,
            "message": "Freshness score calculated."
        }
