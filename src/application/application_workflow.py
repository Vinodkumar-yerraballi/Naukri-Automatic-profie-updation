from src.application.permission import PermissionManager
from src.application.apply_engine import ApplyEngine
from src.application.application_tracker import ApplicationTracker
from src.application.captcha_handler import CaptchaHandler
from src.notification.notifier import Notifier

class ApplicationWorkflow:
    """
    Coordinates the complete application workflow.

    This workflow does not bypass CAPTCHA or OTP.
    It stops and requires manual user action when
    a security challenge is detected.
    """

    def __init__(
        self,
        permission_manager,
        application_tracker,
        captcha_handler,
        notifier
    ):
        self.permission_manager = permission_manager

        self.apply_engine = ApplyEngine(
            permission_manager
        )

        self.application_tracker = application_tracker
        self.captcha_handler = captcha_handler
        self.notifier = notifier

    def process_job(
        self,
        job: dict,
        page_text: str = ""
    ) -> dict:
        """
        Process a job through the application workflow.
        """

        job_url = job.get("job_url")
        job_title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        score = job.get("match_score", 0)

        # Step 1: Check permission

        permission_status = (
            self.permission_manager.get_permission_status(
                score
            )
        )

        # Job does not meet minimum score

        if permission_status == "REJECTED":

            self.application_tracker.mark_rejected(
                job_url
            )

            self.notifier.notify_application_status(
                job_title,
                company,
                "REJECTED"
            )

            return {
                "success": False,
                "status": "REJECTED",
                "message": (
                    "Job does not meet the minimum score."
                )
            }

        # Job requires user review

        if permission_status == "REVIEW":

            self.application_tracker.mark_review(
                job_url
            )

            self.notifier.notify_review_required(
                job_title,
                company,
                score
            )

            return {
                "success": False,
                "status": "REVIEW",
                "message": (
                    "User review is required."
                )
            }

        # Step 2: Check CAPTCHA / OTP

        challenge_detected = (
            self.captcha_handler.detect_challenge(
                page_text
            )
        )

        if challenge_detected:

            challenge_type = (
                self.captcha_handler.get_challenge_type()
            )

            self.notifier.notify_security_challenge(
                challenge_type
            )

            return {
                "success": False,
                "status": "SECURITY_CHALLENGE",
                "challenge_type": challenge_type,
                "message": (
                    "Manual user action is required."
                )
            }

        # Step 3: Check whether application can proceed

        if not self.apply_engine.can_apply(job):

            return {
                "success": False,
                "status": "NOT_APPROVED",
                "message": (
                    "Job has not been approved "
                    "for application."
                )
            }

        # Step 4: Prepare application

        application = (
            self.apply_engine.prepare_application(
                job
            )
        )

        if not application["success"]:

            return application

        # Step 5: Mark as approved

        self.application_tracker.mark_approved(
            job_url
        )

        self.notifier.notify_application_status(
            job_title,
            company,
            "APPROVED"
        )

        return {
            "success": True,
            "status": "READY",
            "application": application
        }