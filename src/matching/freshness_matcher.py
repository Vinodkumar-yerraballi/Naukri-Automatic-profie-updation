
import re


class FreshnessMatcher:
    """Score jobs according to how recently they were posted."""

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
