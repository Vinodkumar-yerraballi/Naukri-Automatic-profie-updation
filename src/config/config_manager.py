import yaml


class ConfigManager:
    """
    Loads job automation configuration files.
    """

    def __init__(
        self,
        preferences_path: str = "config/job_preferences.yaml"
    ):
        self.preferences_path = preferences_path
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> dict:
        """
        Load job preferences from YAML.
        """

        with open(
            self.preferences_path,
            "r",
            encoding="utf-8"
        ) as file:

            return yaml.safe_load(file)

    def get_job_search_config(self) -> dict:
        """
        Return job search configuration.
        """

        return self.preferences.get(
            "job_search",
            {}
        )

    def get_matching_config(self) -> dict:
        """
        Return matching configuration.
        """

        return self.preferences.get(
            "matching",
            {}
        )

    def get_application_config(self) -> dict:
        """
        Return application configuration.
        """

        return self.preferences.get(
            "application",
            {}
        )

    def get_minimum_score(self) -> float:
        """
        Return the minimum job matching score.
        """

        matching_config = self.get_matching_config()

        return float(
            matching_config.get(
                "minimum_score",
                85
            )
        )

    def get_score_weights(self) -> dict:
        """
        Return all job scoring weights.
        """

        matching_config = self.get_matching_config()

        return {
            "role_weight": matching_config.get(
                "role_weight",
                25
            ),
            "skill_weight": matching_config.get(
                "skill_weight",
                30
            ),
            "experience_weight": matching_config.get(
                "experience_weight",
                20
            ),
            "location_weight": matching_config.get(
                "location_weight",
                10
            ),
            "education_weight": matching_config.get(
                "education_weight",
                5
            ),
            "freshness_weight": matching_config.get(
                "freshness_weight",
                5
            ),
            "salary_weight": matching_config.get(
                "salary_weight",
                5
            )
        }