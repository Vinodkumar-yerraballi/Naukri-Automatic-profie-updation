class RoleMatcher:
    """
    Matches a job title against the candidate's target roles.
    """

    def __init__(self, target_roles: list):
        self.target_roles = [
            role.strip().lower()
            for role in target_roles
        ]

    def match_role(self, job_title: str) -> bool:
        """
        Check whether the job title matches
        any of the candidate's target roles.
        """

        if not job_title:
            return False

        job_title = job_title.lower().strip()

        for role in self.target_roles:
            if role in job_title:
                return True

        return False

    def get_match_result(self, job_title: str) -> dict:
        """
        Return detailed role matching information.
        """

        matched = self.match_role(job_title)

        matched_role = None

        if matched:
            for role in self.target_roles:
                if role in job_title.lower():
                    matched_role = role
                    break

        return {
            "job_title": job_title,
            "match": matched,
            "matched_role": matched_role
        }