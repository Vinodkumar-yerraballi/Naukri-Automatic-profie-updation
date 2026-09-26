import re
from src.extraction.skill_dictionary import JOB_SKILLS


class JDExtractor:

    def __init__(self, job_description: str):
        self.job_description = job_description

    def extract_experience(self) -> str:
        patterns = [
            r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\s*to\s*(\d+)\s*(?:years?|yrs?)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                self.job_description,
                re.IGNORECASE
            )

            if match:
                return f"{int(match.group(1))}-{int(match.group(2))} years"

        plus_pattern = r"(\d+)\s*\+\s*(?:years?|yrs?)"

        match = re.search(
            plus_pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return f"{int(match.group(1))}+ years"

        return "Not specified"

    def extract_location(self) -> str:
        pattern = r"Location\s*:\s*(.+)"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_skills(self) -> list:
        """
        Extract technical skills from the job description.

        Uses word-boundary matching so that short/common terms
        are not incorrectly matched inside other words.
        """

        found_skills = []
        jd_lower = self.job_description.lower()

        for skill in JOB_SKILLS:

            skill_lower = skill.lower().strip()

            if not skill_lower:
                continue

            # Escape special regex characters such as
            # +, ., #, etc.
            escaped_skill = re.escape(skill_lower)

            # Word-boundary matching
            pattern = rf"(?<!\w){escaped_skill}(?!\w)"

            if re.search(pattern, jd_lower):
                found_skills.append(skill)

        return found_skills

    def extract_title(self) -> str:
        """
        Extract the job title from the beginning of the JD.

        The actual Naukri job title is normally supplied separately
        through job_metadata, so this is only a fallback.
        """

        lines = [
            line.strip()
            for line in self.job_description.splitlines()
            if line.strip()
        ]

        if not lines:
            return "Not specified"

        # Ignore generic JD headings
        ignored_titles = {
            "job description",
            "job details",
            "description",
            "about the job",
            "role description"
        }

        for line in lines:
            if line.lower() not in ignored_titles:
                return line

        return "Not specified"

    def extract_company(self) -> str:
        pattern = r"([A-Za-z0-9&., ]+)\s+is\s+looking\s+for"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_all(self) -> dict:
        return {
            "title": self.extract_title(),
            "company": self.extract_company(),
            "location": self.extract_location(),
            "experience": self.extract_experience(),
            "skills": self.extract_skills(),
            "job_description": self.job_description
        }