class ApplyEngine:
    """
    Controls the application workflow for approved jobs.
    """
    def __init__(self,permission_manager):
        self.permission_manager=permission_manager

    def can_apply(self,job:dict)->bool:
        """
        Check whether the job is eligible for application.
        """
        score=job.get("match_score",0)
        status=self.permission_manager.get_permission_status(
            score
        )
        return status =="APPROVED"
    def prepare_application(self,job:dict)->dict:
        """
        Prepare an application request for an approved job.

        No external application is submitted here.
        """
        if not self.can_apply(job):
            return {
                "success": False,
                "status": "NOT_APPROVED",
                "message": "Job has not been approved for application."
            }
        return {
            "success": True,
            "status": "READY",
            "job_url": job.get("job_url"),
            "company": job.get("company"),
            "job_title": job.get("title"),
            "message": "Job is ready for the application workflow."
        }
