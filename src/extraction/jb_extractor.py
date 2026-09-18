import re


class JDExtractor:
    """
    A class to extract relevant information from job descriptions.
    """

    def __init__(self, job_description: str):
        self.job_description = job_description

    def extract_experience(self) -> str:
        """
        Extract the required experience from the job description.
        """

        experience_pattern = r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)"

        match = re.search(
            experience_pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            minimum = match.group(1)
            maximum = match.group(2)

            return f"{minimum}-{maximum} years"

        return "Not specified"

    def extract_location(self) -> str:
        """
        Extract the location from the job description.
        """

        pattern = r"Location\s*:\s*(.+)"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_skills(self, known_skills: list) -> list:
        """
        Find known candidate skills mentioned in the job description.
        """

        found_skills = []

        jd_lower = self.job_description.lower()

        for skill in known_skills:

            if skill.lower() in jd_lower:
                found_skills.append(skill)

        return found_skills

    def extract_title(self) -> str:
        """
        Extract the job title from the first non-empty line.
        """

        lines = [
            line.strip()
            for line in self.job_description.splitlines()
            if line.strip()
        ]

        if lines:
            return lines[0]

        return "Not specified"

    def extract_company(self) -> str:
        """
        Extract the company name from the job description.
        """

        pattern = r"([A-Za-z0-9&., ]+)\s+is\s+looking\s+for"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_all(self, known_skills: list) -> dict:
        """
        Extract all available information from the job description.
        """

        return {
            "title": self.extract_title(),
            "company": self.extract_company(),
            "location": self.extract_location(),
            "experience": self.extract_experience(),
            "skills": self.extract_skills(known_skills),
            "job_description": self.job_description
        }