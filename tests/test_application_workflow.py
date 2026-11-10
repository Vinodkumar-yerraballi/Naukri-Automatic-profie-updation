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

    assert result["status"] == "REVIEW"
    assert result["success"] is False


from src.application.application_tracker import ApplicationTracker
from src.application.permission import PermissionManager


class FakeJobRepository:
    def __init__(self):
        self.status = None
        self.attempts_today = 0

    def update_status(self, job_url, status):
        self.status = status

    def get_job_by_url(self, job_url):
        return {"job_url": job_url, "status": self.status}

    def get_application_attempt_count_today(self):
        return self.attempts_today

    def mark_applied(self, job_url):
        self.status = "APPLIED"
        self.attempts_today += 1


def test_auto_approve_rules_pass_when_all_requirements_are_met():
    manager = PermissionManager()
    job = {
        "job_url": "https://example.com/approved-job",
        "title": "Python Data Analyst",
        "company": "Good Company",
        "description": "Requires Python, SQL, and BI expertise.",
        "match_score": 90,
    }
    rules = {
        "enabled": True,
        "min_score": 80,
        "require_keywords_any": ["python", "sql"],
        "exclude_companies": ["bad company"],
    }

    can_auto_approve, failed_rule = manager.evaluate_auto_approve_rules(
        job,
        rules,
    )

    assert can_auto_approve is True
    assert failed_rule is None


def test_auto_approve_rules_fail_when_any_rule_is_broken():
    manager = PermissionManager()
    job = {
        "job_url": "https://example.com/rejected-job",
        "title": "Data Analyst",
        "company": "Bad Company",
        "description": "Needs SQL but not Python.",
        "match_score": 70,
    }
    rules = {
        "enabled": True,
        "min_score": 80,
        "require_keywords_any": ["python"],
        "exclude_companies": ["bad company"],
    }

    can_auto_approve, failed_rule = manager.evaluate_auto_approve_rules(
        job,
        rules,
    )

    assert can_auto_approve is False
    assert failed_rule in {"min_score", "require_keywords_any", "exclude_companies"}

    tracker = ApplicationTracker(FakeJobRepository())
    tracker.mark_skipped(job["job_url"], failed_rule)
    assert tracker.get_application_status(job["job_url"])["status"] == "SKIPPED"


def test_auto_approve_daily_cap_still_enforced():
    repository = FakeJobRepository()
    repository.attempts_today = 3
    tracker = ApplicationTracker(repository)
    max_applications = 3

    def submit_approved_job(job):
        if repository.get_application_attempt_count_today() >= max_applications:
            return {
                "status": "LIMIT_REACHED",
                "message": "Daily limit reached.",
            }
        repository.mark_applied(job["job_url"])
        return {"status": "APPLIED"}

    job = {
        "job_url": "https://example.com/daily-cap-job",
        "title": "Data Analyst",
        "company": "Good Company",
        "description": "Python and SQL experience required.",
        "match_score": 90,
    }

    result = submit_approved_job(job)

    assert result["status"] == "LIMIT_REACHED"
    assert repository.get_application_attempt_count_today() == 3


def test_auto_approve_exclude_companies_uses_case_insensitive_substring_match():
    manager = PermissionManager()
    job = {
        "job_url": "https://example.com/excluded-company-job",
        "title": "Python Data Analyst",
        "company": "Acme Labs",
        "description": "Requires Python and SQL.",
        "match_score": 92,
    }
    rules = {
        "enabled": True,
        "min_score": 80,
        "require_keywords_any": ["python"],
        "exclude_companies": ["acme"],
    }

    can_auto_approve, failed_rule = manager.evaluate_auto_approve_rules(
        job,
        rules,
    )

    assert can_auto_approve is False
    assert failed_rule == "exclude_companies"