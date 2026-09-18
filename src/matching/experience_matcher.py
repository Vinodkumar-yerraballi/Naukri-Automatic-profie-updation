import re


class ExperienceMatcher:
    """
    Compares job experience requirements with
    the candidate's allowed experience range.
    """

    def __init__(
        self,
        candidate_min_experience: int = 0,
        candidate_max_experience: int = 2
    ):
        self.candidate_min_experience = (
            candidate_min_experience
        )

        self.candidate_max_experience = (
            candidate_max_experience
        )

    def parse_experience(
        self,
        experience_text: str
    ) -> tuple:
        """
        Convert experience text into minimum
        and maximum years.
        """

        if not experience_text:
            return None, None

        text = experience_text.lower().strip()

        # Example:
        # 0-2 years
        # 1-3 years
        pattern = r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)"

        match = re.search(pattern, text)

        if match:
            minimum = int(match.group(1))
            maximum = int(match.group(2))

            return minimum, maximum

        # Example:
        # 3+ years
        pattern = r"(\d+)\s*\+\s*(?:years?|yrs?)"

        match = re.search(pattern, text)

        if match:
            minimum = int(match.group(1))

            return minimum, None

        # Example:
        # 2 years
        pattern = r"(\d+)\s*(?:years?|yrs?)"

        match = re.search(pattern, text)

        if match:
            minimum = int(match.group(1))

            return minimum, minimum

        return None, None

    def is_match(
        self,
        job_experience: str
    ) -> bool:
        """
        Determine whether the job experience
        requirement fits the candidate's range.
        """

        job_min, job_max = self.parse_experience(
            job_experience
        )

        # Experience not specified
        if job_min is None:
            return False

        # Example: 3+ years
        if job_max is None:

            return (
                job_min
                <= self.candidate_max_experience
            )

        # Check whether experience ranges overlap
        return (
            job_min <= self.candidate_max_experience
            and
            job_max >= self.candidate_min_experience
        )

    def get_match_result(
        self,
        job_experience: str
    ) -> dict:
        """
        Return detailed experience matching result.
        """

        job_min, job_max = self.parse_experience(
            job_experience
        )

        matched = self.is_match(
            job_experience
        )

        return {
            "job_min_experience": job_min,
            "job_max_experience": job_max,
            "candidate_min_experience":
                self.candidate_min_experience,
            "candidate_max_experience":
                self.candidate_max_experience,
            "match": matched
        }