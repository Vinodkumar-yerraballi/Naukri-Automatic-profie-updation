class JobScorer:
    """
    Calculates the overall match score for a job.
    """

    def __init__(
        self,
        role_weight: float = 25,
        skill_weight: float = 30,
        experience_weight: float = 20,
        location_weight: float = 10,
        education_weight: float = 5,
        freshness_weight: float = 5,
        salary_weight: float = 5
    ):
        self.role_weight = role_weight
        self.skill_weight = skill_weight
        self.experience_weight = experience_weight
        self.location_weight = location_weight
        self.education_weight = education_weight
        self.freshness_weight = freshness_weight
        self.salary_weight = salary_weight

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
        """
        Calculate the weighted job match score.
        """

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
        """
        Convert the numerical score into a category.
        """

        if score >= 90:
            return "Excellent Match"

        if score >= 80:
            return "Strong Match"

        if score >= 70:
            return "Moderate Match"

        if score >= 60:
            return "Weak Match"

        return "Poor Match"