from datetime import datetime

class ApplicationTracker:
    """
    Tracks the status of job applications.
    """
    def __init__(self,repository):
        self.repository=repository

    def mark_review(self,job_url:str):
        """
        Mark a job as waiting for user review.
        """
        self.repository.update_status(job_url,"REVIEW")
    def mark_approved(self,job_url:str):
        """
        Mark a job as waiting for user Approved.
        """
        self.repository.update_status(job_url,"APPROVED")

    def mark_applied(self,job_url:str):
        """
        Mark a job as applied and record the application date.
        """
        self.repository.mark_applied(job_url)

    def mark_application_unconfirmed(self,job_url:str):
        """Prevent an uncertain submission from being attempted twice."""
        self.repository.mark_application_unconfirmed(job_url)

    def mark_already_applied(self,job_url:str):
        """Record an application that Naukri reports as already submitted."""
        self.repository.update_status(job_url,"APPLIED")

    def mark_rejected(self,job_url:str):
        """
        Mark a job as waiting for user review.
        """
        self.repository.update_status(
            job_url,"REJECTED"
        )
    def get_application_status(self,job_url:str):
        """
        Get the current application status.
        """
        job=self.repository.get_job_by_url(job_url)
        if not job:
            return {
                "found" : False,
                "status":None
            }
        return {
            "found":True,
            "status":job.get("status"),
            "job_url":job_url
        }
