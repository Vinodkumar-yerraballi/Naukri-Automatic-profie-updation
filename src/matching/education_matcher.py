
import re
from typing import List, Optional


class EducationMatcher:
    """Match candidate qualifications against job requirements."""

    EDUCATION_ALIASES = {
        "msc": "master of science",
        "m.sc": "master of science",
        "bsc": "bachelor of science",
        "b.sc": "bachelor of science",
        "mtech": "master of technology",
        "m.tech": "master of technology",
        "btech": "bachelor of technology",
        "b.tech": "bachelor of technology",
        "mba": "master of business administration",
        "bca": "bachelor of computer applications",
        "mca": "master of computer applications",
        "phd": "doctor of philosophy",
    }

    def __init__(self, candidate_education: Optional[List[str]] = None):
        self.candidate_education = candidate_education or []

    
    @classmethod
    def normalize(cls, qualification: str) -> str:
        """Normalize qualification abbreviations and punctuation."""
        text = qualification.lower().strip()
        text = re.sub(r"[.,]", "", text)
        text = re.sub(r"\s+", " ", text)

        aliases = {
            "msc": "master of science",
            "bsc": "bachelor of science",
            "mtech": "master of technology",
            "btech": "bachelor of technology",
            "mba": "master of business administration",
            "bca": "bachelor of computer applications",
            "mca": "master of computer applications",
            "phd": "doctor of philosophy",
        }

        # Normalize the degree abbreviation while preserving specialization.
        parts = text.split(maxsplit=1)
        degree = parts[0] if parts else ""
        specialization = parts[1] if len(parts) > 1 else ""

        normalized_degree = aliases.get(degree, degree)

        if specialization:
            return f"{normalized_degree} {specialization}"

        return normalized_degree


    def get_match_result(self, job_requirements) -> dict:
        """
        Return a match score from 0 to 100.

        Unknown requirements receive None so the evaluator can
        exclude them instead of assuming a match.
        """
        if not job_requirements:
            return {
                "match": None,
                "score": None,
                "candidate_education": self.candidate_education,
                "job_requirements": [],
                "matched_qualifications": [],
                "message": "Education requirement not specified.",
            }

        if isinstance(job_requirements, str):
            job_requirements = [job_requirements]

        candidate_qualifications = [
            self.normalize(item)
            for item in self.candidate_education
            if item
        ]

        required_qualifications = [
            self.normalize(item)
            for item in job_requirements
            if item
        ]

        if not required_qualifications:
            return {
                "match": None,
                "score": None,
                "candidate_education": self.candidate_education,
                "job_requirements": [],
                "matched_qualifications": [],
                "message": "Education requirement not specified.",
            }

        matched = [
            requirement
            for requirement in required_qualifications
            if any(
                requirement in candidate
                or candidate in requirement
                for candidate in candidate_qualifications
            )
        ]

        score = round(
            len(matched) / len(required_qualifications) * 100, 2
        )

        return {
            "match": score > 0,
            "score": score,
            "candidate_education": self.candidate_education,
            "job_requirements": job_requirements,
            "matched_qualifications": matched,
            "message": (
                "Education requirement matched."
                if score > 0
                else "No matching education qualification found."
            ),
        }
