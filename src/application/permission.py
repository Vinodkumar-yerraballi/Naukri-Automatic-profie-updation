from src.config.config_manager import ConfigManager


class PermissionManager:
    """
    Checks job eligibility and routes eligible jobs for human review.
    """

    def __init__(self):
        config_manager = ConfigManager()
        self.minimum_score = config_manager.get_minimum_score()

    def check_score(self, score: float) -> bool:
        """
        Check whether the job meets the minimum score.
        """
        return score >= self.minimum_score

    def requires_review(self, score: float) -> bool:
        """
        Determine whether the job requires user review.
        """
        return self.check_score(score)

    def get_permission_status(self, score: float) -> str:
        """
        Return the current permission status.
        """
        if not self.check_score(score):
            return "REJECTED"
        return "REVIEW"

    def evaluate_auto_approve_rules(
        self,
        job: dict,
        auto_approve_rules: dict | None = None,
    ) -> tuple[bool, str | None]:
        """Return whether a job can auto-apply and the failing rule name."""
        rules = auto_approve_rules or {}
        if not rules.get("enabled", False):
            return True, None

        score = float(job.get("match_score", 0) or 0)
        min_score = float(rules.get("min_score", self.minimum_score))
        if score < min_score:
            return False, "min_score"

        required_keywords = [
            str(keyword).strip().lower()
            for keyword in rules.get("require_keywords_any", [])
            if str(keyword).strip()
        ]
        if required_keywords:
            job_text = (
                f"{job.get('title', '')} {job.get('description', '')}"
            ).lower()
            normalized_keywords = {
                keyword: keyword in job_text
                for keyword in required_keywords
            }
            if not any(normalized_keywords.values()):
                return False, "require_keywords_any"

        excluded_companies = [
            str(company).strip().lower()
            for company in rules.get("exclude_companies", [])
            if str(company).strip()
        ]
        company_name = str(job.get("company", "")).lower()
        if excluded_companies and any(
            company in company_name for company in excluded_companies
        ):
            return False, "exclude_companies"

        return True, None
