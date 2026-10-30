import json

import pytest

from src.profile.platform_resume_uploader import (
    CandidatePlatformBrowser,
    PlatformProfileUpdater,
    PlatformResumeUploader,
)


class FakeBrowser:
    def __init__(self):
        self.uploaded = []

    def update_profile_resume(self, resume_path):
        self.uploaded.append(resume_path)


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector
        self.first = self

    def count(self):
        if self.selector == "body":
            return 1
        if self.selector == "input[type='file']":
            return 1
        if "button:has-text('Upload')" in self.selector:
            return 1
        return 0

    def inner_text(self):
        return self.page.body

    def set_input_files(self, path):
        self.page.uploaded_file = path

    def is_visible(self):
        return True

    def click(self, timeout):
        self.page.body = "Resume uploaded successfully"


class FakePage:
    url = "https://www.foundit.in/seeker/profile"
    body = "Candidate profile"

    def locator(self, selector):
        return FakeLocator(self, selector)

    def goto(self, *args, **kwargs):
        pass

    def wait_for_timeout(self, timeout):
        pass


class MultipleInputPage(FakePage):
    def locator(self, selector):
        locator = FakeLocator(self, selector)
        if selector == "input[type='file']":
            locator.count = lambda: 2
        return locator


def test_uploads_changed_resume_and_records_hash(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    state_path = tmp_path / "foundit-state.json"
    browser = FakeBrowser()
    uploader = PlatformResumeUploader("foundit", state_path)

    assert uploader.update_if_changed(browser, resume) is True
    assert browser.uploaded == [resume]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["file_name"] == "resume.pdf"
    assert state["sha256"]
    assert state["uploaded_at"]


def test_skips_upload_when_resume_hash_has_not_changed(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    browser = FakeBrowser()
    uploader = PlatformResumeUploader("indeed", tmp_path / "state.json")

    assert uploader.update_if_changed(browser, resume) is True
    assert uploader.update_if_changed(browser, resume) is False
    assert browser.uploaded == [resume]


def test_upload_failure_does_not_record_new_hash(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume v1")
    state_path = tmp_path / "state.json"
    uploader = PlatformResumeUploader("foundit", state_path)

    class FailingBrowser:
        def update_profile_resume(self, resume_path):
            raise RuntimeError("profile upload was not confirmed")

    with pytest.raises(RuntimeError, match="not confirmed"):
        uploader.update_if_changed(FailingBrowser(), resume)

    assert not state_path.exists()


def test_missing_source_resume_is_reported(tmp_path):
    uploader = PlatformResumeUploader("foundit", tmp_path / "state.json")

    with pytest.raises(FileNotFoundError, match="Resume file not found"):
        uploader.update_if_changed(
            FakeBrowser(),
            tmp_path / "missing.pdf",
        )


def test_platform_browser_uploads_and_requires_confirmation(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    browser = CandidatePlatformBrowser("foundit")
    browser.page = page

    browser.update_profile_resume(resume)

    assert page.uploaded_file == str(resume.resolve())
    assert page.body == "Resume uploaded successfully"


def test_platform_browser_rejects_unsupported_platform():
    with pytest.raises(ValueError, match="Unsupported resume platform"):
        CandidatePlatformBrowser("wellfound")


def test_platform_browser_rejects_unimplemented_profile_fields():
    browser = CandidatePlatformBrowser("indeed")

    with pytest.raises(
        RuntimeError,
        match="not implemented for Indeed",
    ):
        browser.update_profile_fields({"data": {}})


def test_foundit_skills_use_editable_search_and_save_selector(tmp_path):
    class ReadOnlySkillField:
        def __init__(self):
            self.click_count = 0

        def count(self):
            return 1

        def click(self, timeout):
            self.click_count += 1

        def fill(self, value):
            raise AssertionError("The readonly skill field must not be filled")

    class SearchField:
        def __init__(self, page):
            self.page = page
            self.last = self

        def count(self):
            return 1

        def is_visible(self):
            return True

        def fill(self, value):
            self.page.search_value = value

    class Option:
        def __init__(self, page):
            self.page = page

        def is_visible(self):
            return True

        def inner_text(self):
            return self.page.search_value

        def click(self, timeout):
            self.page.selected.append(self.page.search_value)

    class Modal:
        def __init__(self, page):
            self.page = page
            self.skill_field = ReadOnlySkillField()
            self.search_field = SearchField(page)

        def locator(self, selector):
            if selector == "#skills":
                return self.skill_field
            if selector == "input:not([readonly]):not([type='hidden'])":
                return self.search_field
            if selector == "button":
                return FakeButtons()
            raise AssertionError(f"Unexpected modal selector: {selector}")

    class FakeButtons:
        def all_inner_texts(self):
            return []

    class Page:
        def __init__(self):
            self.search_value = ""
            self.selected = []

        def locator(self, selector):
            assert selector == "li, [role='option']"
            return FakeOptions(self)

        def wait_for_timeout(self, timeout):
            pass

    class FakeOptions:
        def __init__(self, page):
            self.page = page

        def all(self):
            return [Option(self.page)]

    browser = CandidatePlatformBrowser("foundit")
    browser.page = Page()
    modal = Modal(browser.page)
    browser._open_foundit_modal = lambda heading: modal
    saved = []
    browser._save_foundit_modal = lambda opened_modal: saved.append(
        opened_modal
    )

    assert browser._update_foundit_skills(["Python"]) is True
    assert modal.skill_field.click_count == 1
    assert browser.page.selected == ["Python"]
    assert saved == [modal]


def test_platform_browser_can_share_playwright_instance(tmp_path):
    class FakeContext:
        def __init__(self):
            self.closed = False
            self.pages = [FakePage()]
            self.new_page_calls = 0

        def new_page(self):
            self.new_page_calls += 1
            return FakePage()

        def close(self):
            self.closed = True

    class FakeChromium:
        def __init__(self):
            self.context = FakeContext()

        def launch_persistent_context(self, **kwargs):
            return self.context

    class FakePlaywright:
        def __init__(self):
            self.chromium = FakeChromium()
            self.stopped = False

        def stop(self):
            self.stopped = True

    shared_playwright = FakePlaywright()
    browser = CandidatePlatformBrowser("foundit")

    browser.start_persistent(tmp_path / "foundit_profile", shared_playwright)
    assert browser.page is shared_playwright.chromium.context.pages[0]
    assert shared_playwright.chromium.context.new_page_calls == 0
    browser.close()

    assert shared_playwright.chromium.context.closed is True
    assert shared_playwright.stopped is False


def test_platform_browser_stops_when_file_input_is_ambiguous(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    browser = CandidatePlatformBrowser("indeed")
    browser.page = MultipleInputPage()

    with pytest.raises(RuntimeError, match="Multiple file upload controls"):
        browser.update_profile_resume(resume)


def test_profile_updater_tracks_successful_resume_version(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    state_path = tmp_path / "profile-state.json"
    updater = PlatformProfileUpdater("foundit", state_path)

    class FakeProfileBrowser:
        def __init__(self):
            self.proposals = []

        def update_profile_fields(self, proposal):
            self.proposals.append(proposal)
            return ["skills", "employment", "projects"]

    browser = FakeProfileBrowser()
    proposal = {"data": {"skills": ["Python"]}}

    assert updater.is_current(resume) is False
    assert updater.update_if_changed(browser, resume, proposal) == [
        "skills",
        "employment",
        "projects",
    ]
    assert updater.is_current(resume) is True
    assert updater.update_if_changed(browser, resume, proposal) == []
    assert browser.proposals == [proposal]


def test_profile_updater_can_reconcile_unchanged_foundit_resume(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    updater = PlatformProfileUpdater("foundit", tmp_path / "profile-state.json")
    proposal = {"data": {"skills": ["Python"]}}

    class FakeProfileBrowser:
        def __init__(self):
            self.calls = 0

        def update_profile_fields(self, proposal):
            self.calls += 1
            return ["skills"]

    browser = FakeProfileBrowser()
    assert updater.update_if_changed(browser, resume, proposal) == ["skills"]
    assert updater.is_current(resume) is True

    assert updater.update_if_changed(browser, resume, proposal) == []
    assert updater.update_if_changed(
        browser,
        resume,
        proposal,
        force=True,
    ) == ["skills"]
    assert browser.calls == 2


def test_profile_updater_supports_naukri_state(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    state_path = tmp_path / "naukri-profile-state.json"
    updater = PlatformProfileUpdater(
        "naukri",
        state_path,
    )

    assert updater.is_current(resume) is False

    class FakeNaukriProfileBrowser:
        def update_profile_fields(self, proposal):
            assert proposal == {"data": {"headline": "Data Analyst"}}
            return ["headline", "skills", "projects"]

    updated_fields = updater.update_if_changed(
        FakeNaukriProfileBrowser(),
        resume,
        {"data": {"headline": "Data Analyst"}},
    )

    assert updated_fields == ["headline", "skills", "projects"]
    assert updater.is_current(resume) is True
    assert json.loads(state_path.read_text(encoding="utf-8"))["sha256"]


def test_profile_updater_does_not_record_failed_update(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    state_path = tmp_path / "profile-state.json"
    updater = PlatformProfileUpdater("foundit", state_path)

    class FailingProfileBrowser:
        def update_profile_fields(self, proposal):
            raise RuntimeError("profile fields were not saved")

    with pytest.raises(RuntimeError, match="not saved"):
        updater.update_if_changed(
            FailingProfileBrowser(),
            resume,
            {"data": {}},
        )

    assert not state_path.exists()


def test_foundit_date_parts_are_only_returned_when_year_is_known():
    assert CandidatePlatformBrowser._date_parts("April 2021") == (
        "2021",
        "April",
    )
    assert CandidatePlatformBrowser._date_parts("2021-2023") == (
        "2021",
        None,
    )
    assert CandidatePlatformBrowser._date_parts("Present") == (None, None)
