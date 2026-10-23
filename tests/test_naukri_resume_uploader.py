import json

import pytest

from src.profile.naukri_resume_uploader import NaukriResumeUploader


class FakeBrowser:
    def __init__(self):
        self.uploaded = []

    def update_profile_resume(self, resume_path):
        self.uploaded.append(resume_path)


def test_uploads_changed_resume_and_records_hash(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    state_path = tmp_path / "state.json"
    browser = FakeBrowser()
    uploader = NaukriResumeUploader(state_path)

    uploaded = uploader.update_if_changed(browser, resume)

    assert uploaded is True
    assert browser.uploaded == [resume]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["file_name"] == "resume.pdf"
    assert state["sha256"]
    assert state["uploaded_at"]


def test_skips_upload_when_resume_hash_has_not_changed(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    state_path = tmp_path / "state.json"
    browser = FakeBrowser()
    uploader = NaukriResumeUploader(state_path)

    uploader.update_if_changed(browser, resume)
    uploaded_again = uploader.update_if_changed(browser, resume)

    assert uploaded_again is False
    assert browser.uploaded == [resume]


def test_upload_failure_does_not_record_new_hash(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    state_path = tmp_path / "state.json"
    uploader = NaukriResumeUploader(state_path)

    class FailingBrowser:
        def update_profile_resume(self, resume_path):
            raise RuntimeError("profile upload was not confirmed")

    with pytest.raises(RuntimeError, match="not confirmed"):
        uploader.update_if_changed(FailingBrowser(), resume)

    assert not state_path.exists()


def test_missing_source_resume_is_reported(tmp_path):
    uploader = NaukriResumeUploader(tmp_path / "state.json")

    with pytest.raises(FileNotFoundError, match="Resume file not found"):
        uploader.update_if_changed(FakeBrowser(), tmp_path / "missing.pdf")
