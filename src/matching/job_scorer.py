from src.config.config_manager import ConfigManager


class JobScorer:

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
        role_match,
        skill_match,
        experience_match,
        location_match=0,
        education_match=None,
        freshness_match=None,
        salary_match=None
    ):
        """
        Calculate the weighted job match score.

        Each match value should be between 0 and 100.

        The score is normalized using only the components that
        are currently available, so unused components do not
        artificially reduce the maximum score.
        """

        components = [
            (role_match, self.role_weight),
            (skill_match, self.skill_weight),
            (experience_match, self.experience_weight),
            (location_match, self.location_weight),
        ]

        # Add optional components only when they are actually
        # provided by the evaluator.
        if education_match is not None:
            components.append(
                (education_match, self.education_weight)
            )

        if freshness_match is not None:
            components.append(
                (freshness_match, self.freshness_weight)
            )

        if salary_match is not None:
            components.append(
                (salary_match, self.salary_weight)
            )

        total_weight = sum(weight for _, weight in components)

        if total_weight == 0:
            return 0.0

        weighted_score = sum(
            match_value * weight
            for match_value, weight in components
        )

        score = weighted_score / total_weight

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