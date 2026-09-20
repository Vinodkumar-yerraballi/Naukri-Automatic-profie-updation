from src.config.config_manager import ConfigManager


class JobScorer:
    """
    Calculates the overall match score for a job.
    """

    def __init__(self):
        config_manager = ConfigManager()

        weights = config_manager.get_score_weights()

        self.role_weight = weights["role_weight"]
        self.skill_weight = weights["skill_weight"]
        self.experience_weight = weights["experience_weight"]
        self.location_weight = weights["location_weight"]
        self.education_weight = weights["education_weight"]
        self.freshness_weight = weights["freshness_weight"]
        self.salary_weight = weights["salary_weight"]

    def calculate_score(
        self,
        role_match: float,
        skill_match: float,
        experience_match: float,
        location_match: float = 0,
        education_match: float = 0,
        freshness_match: float = 0,
        salary_match: float = 0
    ) -> float:

        score = (
            role_match * self.role_weight / 100
            + skill_match * self.skill_weight / 100
            + experience_match * self.experience_weight / 100
            + location_match * self.location_weight / 100
            + education_match * self.education_weight / 100
            + freshness_match * self.freshness_weight / 100
            + salary_match * self.salary_weight / 100
        )

        return round(score, 2)

    def get_score_category(self, score: float) -> str:

        if score >= 90:
            return "Excellent Match"

        if score >= 80:
            return "Strong Match"

        if score >= 70:
            return "Moderate Match"

        if score >= 60:
            return "Weak Match"

        return "Poor Match"