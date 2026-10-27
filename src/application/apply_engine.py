class ApplyEngine:
    """
    Controls the application workflow for explicitly approved jobs.
    """

    def __init__(self, permission_manager):
        self.permission_manager = permission_manager

    def can_apply(self, job: dict) -> bool:
        """
        Require both an eligible score and explicit human approval.
        A score alone must never authorize an application.
        """
        score = job.get("match_score", 0)
        permission_status = self.permission_manager.get_permission_status(score)
        return (
            permission_status != "REJECTED"
            and job.get("status") == "APPROVED"
        )

    def prepare_application(self, job: dict) -> dict:
        """
        Prepare an application request for an approved job.

        No external application is submitted here.
        """
        if not self.can_apply(job):
            return {
                "success": False,
                "status": "NOT_APPROVED",
                "message": "Job must meet the score threshold and be explicitly approved.",
            }
        return {
            "success": True,
            "status": "READY",
            "job_url": job.get("job_url"),
            "company": job.get("company"),
            "job_title": job.get("title"),
            "message": "Job is ready for the application workflow.",
        }
