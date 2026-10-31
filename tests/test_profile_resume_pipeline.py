from main import upload_resume_to_enabled_profiles


def test_uploads_selected_resume_to_enabled_resume_profiles(
    tmp_path,
    monkeypatch,
):
    uploads = []
    browsers = []

    class FakeNaukriUploader:
        def __init__(self, state_path):
            self.state_path = state_path

        def update_if_changed(self, browser, resume_path):
            uploads.append(("naukri", resume_path))
            return True

    class FakePlatformBrowser:
        def __init__(self, platform, platform_config):
            self.platform = platform
            self.started = False
            self.closed = False
            browsers.append(self)

        def start_persistent(self, profile_directory, playwright=None):
            self.started = True

        def close(self):
            self.closed = True

    class FakePlatformUploader:
        def __init__(self, platform, state_path):
            self.platform = platform

        def update_if_changed(self, browser, resume_path):
            uploads.append((self.platform, resume_path))
            return True

    monkeypatch.setattr("main.NaukriResumeUploader", FakeNaukriUploader)
    monkeypatch.setattr(
        "main.CandidatePlatformBrowser",
        FakePlatformBrowser,
    )
    monkeypatch.setattr(
        "main.PlatformResumeUploader",
        FakePlatformUploader,
    )

    resume_path = str(tmp_path / "best-job-draft.docx")
    failures = upload_resume_to_enabled_profiles(
        resume_path,
        {"update_resume": True},
        {
            "foundit": {"update_resume": True},
            "indeed": {"update_resume": False},
            "hirist": {"update_resume": True},
        },
        naukri_browser=object(),
        playwright=object(),
    )

    assert failures == []
    assert uploads == [
        ("naukri", resume_path),
        ("foundit", resume_path),
        ("hirist", resume_path),
    ]
    assert all(browser.started and browser.closed for browser in browsers)
