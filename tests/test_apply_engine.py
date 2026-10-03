from src.application.apply_engine import ApplyEngine


class FakePermissionManager:
    def get_permission_status(self, score):
        if score >= 85:
            return "APPROVE"
        return "REJECTED"


def test_can_apply_approved_job():
    permission_manager = FakePermissionManager()
    engine = ApplyEngine(permission_manager)

    job = {
        "match_score": 90
    }

    assert engine.can_apply(job) is True


def test_can_apply_rejected_job():
    permission_manager = FakePermissionManager()
    engine = ApplyEngine(permission_manager)

    job = {
        "match_score": 80
    }

    assert engine.can_apply(job) is False