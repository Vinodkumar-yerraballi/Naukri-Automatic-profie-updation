from src.application.application_workflow import ApplicationWorkflow


class FakePermissionManager:
    def __init__(self, auto_apply=False):
        self.auto_apply = auto_apply

    def get_permission_status(self, score):
        if score < 85:
            return "REJECTED"

        if self.auto_apply:
            return "APPROVE"

        return "REVIEW"


class FakeApplicationTracker:
    def __init__(self):
        self.status = None

    def mark_rejected(self, job_url):
        self.status = "REJECTED"

    def mark_review(self, job_url):
        self.status = "REVIEW"

    def mark_approved(self, job_url):
        self.status = "APPROVED"


class FakeCaptchaHandler:
    def __init__(self, challenge=False):
        self.challenge = challenge

    def detect_challenge(self, page_text):
        return self.challenge

    def get_challenge_type(self):
        return "CAPTCHA"


class FakeNotifier:
    def notify_application_status(self, *args):
        pass

    def notify_review_required(self, *args):
        pass

    def notify_security_challenge(self, *args):
        pass


def create_workflow(auto_apply=False, challenge=False):
    permission_manager = FakePermissionManager(auto_apply)
    tracker = FakeApplicationTracker()
    captcha_handler = FakeCaptchaHandler(challenge)
    notifier = FakeNotifier()

    workflow = ApplicationWorkflow(
        permission_manager,
        tracker,
        captcha_handler,
        notifier
    )

    return workflow


def test_rejected_job():
    workflow = create_workflow()

    job = {
        "job_url": "https://example.com/job1",
        "title": "Data Analyst",
        "company": "Test Company",
        "match_score": 80
    }

    result = workflow.process_job(job)

    assert result["status"] == "REJECTED"
    assert result["success"] is False


def test_review_job():
    workflow = create_workflow()

    job = {
        "job_url": "https://example.com/job2",
        "title": "Data Analyst",
        "company": "Test Company",
        "match_score": 90
    }

    result = workflow.process_job(job)

    assert result["status"] == "REVIEW"
    assert result["success"] is False


def test_security_challenge():
    workflow = create_workflow(challenge=True,auto_apply=True)

    job = {
        "job_url": "https://example.com/job3",
        "title": "Data Analyst",
        "company": "Test Company",
        "match_score": 90
    }

    result = workflow.process_job(
        job,
        page_text="Please complete CAPTCHA"
    )

    assert result["status"] == "SECURITY_CHALLENGE"
    assert result["success"] is False


def test_approved_job():
    workflow = create_workflow(auto_apply=True)

    job = {
        "job_url": "https://example.com/job4",
        "title": "Data Analyst",
        "company": "Test Company",
        "match_score": 90
    }

    result = workflow.process_job(job)

    assert result["status"] == "READY"
    assert result["success"] is True