from datetime import datetime


class Notifier:
    """
    Handles notifications for the job automation system.
    """

    def __init__(self):
        self.notification_history = []

    def send(
        self,
        message: str,
        notification_type: str = "INFO"
    ) -> dict:

        timestamp = datetime.now().isoformat()

        notification = {
            "timestamp": timestamp,
            "type": notification_type,
            "message": message
        }

        self.notification_history.append(notification)

        print("\n========== NOTIFICATION ==========")
        print(f"Time: {timestamp}")
        print(f"Type: {notification_type}")
        print(f"Message: {message}")

        return notification

    def notify_job_match(
        self,
        job_title: str,
        company: str,
        score: float
    ) -> dict:

        message = (
            f"Job match found: {job_title} at {company}. "
            f"Match score: {score}"
        )

        return self.send(
            message,
            "JOB_MATCH"
        )

    def notify_review_required(
        self,
        job_title: str,
        company: str,
        score: float
    ) -> dict:

        message = (
            f"Review required: {job_title} at {company}. "
            f"Match score: {score}"
        )

        return self.send(
            message,
            "REVIEW_REQUIRED"
        )

    def notify_application_status(
        self,
        job_title: str,
        company: str,
        status: str
    ) -> dict:

        message = (
            f"Application status: {job_title} at {company} "
            f"-> {status}"
        )

        return self.send(
            message,
            "APPLICATION_STATUS"
        )

    def notify_security_challenge(
        self,
        challenge_type: str
    ) -> dict:

        message = (
            f"{challenge_type} detected. "
            f"Manual user action is required."
        )

        return self.send(
            message,
            "SECURITY_CHALLENGE"
        )

    def get_history(self) -> list:

        return self.notification_history