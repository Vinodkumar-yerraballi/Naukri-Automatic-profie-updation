from src.application.apply_engine import ApplyEngine


class FakePermissionManager:
    def get_permission_status(self, score):
        if score >= 85:
            return "REVIEW"
        return "REJECTED"


def test_can_apply_approved_job():
    engine = ApplyEngine(FakePermissionManager())
    job = {"match_score": 90, "status": "APPROVED"}

    assert engine.can_apply(job) is True


def test_cannot_apply_job_waiting_for_review():
    engine = ApplyEngine(FakePermissionManager())
    job = {"match_score": 90, "status": "REVIEW"}

    assert engine.can_apply(job) is False


def test_cannot_apply_rejected_or_low_score_job():
    engine = ApplyEngine(FakePermissionManager())
    job = {"match_score": 80, "status": "APPROVED"}

    assert engine.can_apply(job) is False
