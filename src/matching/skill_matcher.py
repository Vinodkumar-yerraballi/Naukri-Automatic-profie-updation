class SkillMatcher:

    SKILL_ALIASES = {
        "statistics": "statistical analysis",
        "statistical analysis": "statistical analysis",

        "powerbi": "power bi",
        "power bi": "power bi",
        "airflow": "apache airflow",
        "apache airflow": "apache airflow",
        "amazon web services": "aws",
        "aws": "aws",
        "microsoft azure": "azure",
        "azure": "azure",
        "google cloud platform": "gcp",
        "gcp": "gcp",

        "ml": "machine learning",
        "machine learning": "machine learning",

        "numpy": "numpy",
        "num py": "numpy",

        "pandas": "pandas",

        "data cleaning": "data cleansing",
        "data cleansing": "data cleansing",

        "data manipulation": "data wrangling",
        "data wrangling": "data wrangling",

        "business intelligence": "business intelligence",
        "bi": "business intelligence",

        "natural language processing": "nlp",
        "nlp": "nlp",

        "scikit learn": "scikit-learn",
        "scikit-learn": "scikit-learn",
        "data analysis": "data analysis",
        "data analytics": "data analysis",
        "data analyst": "data analysis",

        "data management": "data management",
        "data quality": "data quality",

        "eda": "exploratory data analysis",
        "exploratory data analysis": "exploratory data analysis",

        "sql": "sql",
        "python": "python",
        "exploratory data analysis": "exploratory data analysis",
        "eda": "exploratory data analysis",
        "data analysis": "data analysis",
        "data analytics": "data analysis",
    }

    def __init__(self, candidate_skills: list):
        self.candidate_skills = {
            self.normalize_skill(skill)
            for skill in candidate_skills
        }

    @classmethod
    def normalize_skill(cls, skill: str) -> str:
        skill = skill.strip().lower()

        # Use alias if available
        return cls.SKILL_ALIASES.get(skill, skill)

    @classmethod
    def unique_job_skills(cls, job_skills: list) -> list:
        unique_skills = []
        seen = set()
        for skill in job_skills:
            normalized_skill = cls.normalize_skill(skill)
            if normalized_skill not in seen:
                seen.add(normalized_skill)
                unique_skills.append(skill)
        return unique_skills

    def find_matched_skills(self, job_skills: list) -> list:
        matched_skills = []

        for skill in self.unique_job_skills(job_skills):
            normalized_skill = self.normalize_skill(skill)

            if normalized_skill in self.candidate_skills:
                matched_skills.append(skill)

        return matched_skills

    def finding_missing_skills(self, job_skills: list) -> list:
        missing_skills = []

        for skill in self.unique_job_skills(job_skills):
            normalized_skill = self.normalize_skill(skill)

            if normalized_skill not in self.candidate_skills:
                missing_skills.append(skill)

        return missing_skills

    def calculate_match_percentage(self, job_skills: list) -> float:
        unique_job_skills = self.unique_job_skills(job_skills)
        if not unique_job_skills:
            return None

        matched_skills = self.find_matched_skills(unique_job_skills)

        percentage = (
            len(matched_skills) / len(unique_job_skills)
        ) * 100

        return round(percentage, 2)

    def get_match_result(self, job_skills: list) -> dict:
        matched = self.find_matched_skills(job_skills)
        missing = self.finding_missing_skills(job_skills)
        percentage = self.calculate_match_percentage(job_skills)

        return {
            "matched_skills": matched,
            "missing_skills": missing,
            "match_percentage": percentage
        }