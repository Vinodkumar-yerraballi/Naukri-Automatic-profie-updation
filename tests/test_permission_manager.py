from src.application.permission import PermissionManager


class FakeConfigManager:
    def get_minimum_score(self):
        return 85


def test_eligible_jobs_are_always_sent_to_review(monkeypatch):
    monkeypatch.setattr(
        "src.application.permission.ConfigManager",
        FakeConfigManager,
    )

    permission_manager = PermissionManager()

    assert permission_manager.get_permission_status(90) == "REVIEW"
    assert permission_manager.requires_review(90) is True


def test_below_threshold_jobs_are_rejected(monkeypatch):
    monkeypatch.setattr(
        "src.application.permission.ConfigManager",
        FakeConfigManager,
    )

    permission_manager = PermissionManager()

    assert permission_manager.get_permission_status(84) == "REJECTED"
    assert permission_manager.requires_review(84) is False
