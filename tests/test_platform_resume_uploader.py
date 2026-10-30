import json

import pytest
from playwright.sync_api import Error as PlaywrightError

from src.profile.platform_resume_uploader import (
    CandidatePlatformBrowser,
    PLATFORM_PAGES,
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
        if self.selector in ("input[type='file']", "#myfile"):
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
    page_title = "Candidate Profile"
    response_status = None
    goto_arguments = None

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_role(self, role, name=None, exact=False):
        assert role == "button"
        assert name == "Update"
        assert exact is True
        page = self

        class FakeRoleLocator:
            def count(self):
                return getattr(page, "profile_update_button_count", 0)

            def wait_for(self, state, timeout):
                assert state == "visible"
                page.profile_update_wait_timeout = timeout
                if getattr(page, "reveal_update_button_after_wait", False):
                    page.profile_update_button_count = 1
                if self.count() != 1:
                    raise PlaywrightError("Timed out waiting for Update button")

        return FakeRoleLocator()

    def goto(self, *args, **kwargs):
        self.goto_arguments = (args, kwargs)
        if self.response_status is None:
            return None
        return type("Response", (), {"status": self.response_status})()

    def wait_for_timeout(self, timeout):
        pass

    def title(self):
        return self.page_title

    def evaluate(self, script):
        return {"sessionKey": "sessionValue"}

    def expect_response(self, predicate, timeout):
        response = FakeUploadResponse()
        assert predicate(response)
        return FakeResponseExpectation(response)


class FakeUploadResponse:
    url = "https://www.shine.com/api/v2/candidate/123/resumefiles/"
    status = 201

    def json(self):
        return {"success": True, "data": {"id": 123}}


class FakeResponseExpectation:
    def __init__(self, response):
        self.value = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeSessionContext:
    def __init__(self):
        self.added_cookies = []
        self.init_scripts = []

    def cookies(self, urls=None):
        return [{"name": "shine-session", "value": "test-cookie"}]

    def add_cookies(self, cookies):
        self.added_cookies.extend(cookies)

    def add_init_script(self, script):
        self.init_scripts.append(script)


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


@pytest.mark.parametrize(
    ("status", "title", "body", "message"),
    [
        (404, "Error Page", "Not found", "HTTP 404"),
        (200, "Error Page", "Not found", "page title"),
        (200, "Candidate Onboarding", "404 Not Found", "profile page"),
    ],
)
def test_platform_browser_rejects_unavailable_profile_page(
    tmp_path,
    status,
    title,
    body,
    message,
):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    page.response_status = status
    page.page_title = title
    page.body = body
    browser = CandidatePlatformBrowser(
        "shine",
        platform_config={
            "profile_url": "https://example.test/profile",
        },
    )

    browser.page = page
    with pytest.raises(RuntimeError, match=message):
        browser.update_profile_resume(resume)

    assert not hasattr(page, "uploaded_file")


def test_platform_browser_rejects_shine_login_page(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    page.url = "https://www.shine.com/"
    page.body = "Enter your email /phone number Login Via OTP"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(RuntimeError, match="Shine is displaying its sign-in form"):
        browser.update_profile_resume(resume)

    assert not hasattr(page, "uploaded_file")


def test_platform_browser_rejects_unsupported_platform():
    with pytest.raises(ValueError, match="Unsupported resume platform"):
        CandidatePlatformBrowser("unsupported")


def test_shine_resume_upload_uses_api_response_as_confirmation(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    page.url = "https://www.shine.com/myshine/resume/upload"
    page.body = "Upload Resume"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page
    browser.context = FakeSessionContext()
    browser.session_state_path = tmp_path / "shine-session.json"

    browser.update_profile_resume(resume)

    assert page.uploaded_file == str(resume.resolve())
    state = json.loads(browser.session_state_path.read_text(encoding="utf-8"))
    assert state["cookies"][0]["name"] == "shine-session"
    assert state["session_storage"] == {"sessionKey": "sessionValue"}


def test_shine_resume_upload_rejects_api_failure(tmp_path):
    class FailedUploadResponse(FakeUploadResponse):
        status = 400

    class FailedUploadPage(FakePage):
        def expect_response(self, predicate, timeout):
            response = FailedUploadResponse()
            return FakeResponseExpectation(response)

    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FailedUploadPage()
    page.url = "https://www.shine.com/myshine/resume/upload"
    page.body = "Upload Resume"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(RuntimeError, match="HTTP 400"):
        browser.update_profile_resume(resume)


def test_shine_resume_upload_rejects_files_over_five_megabytes(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    page = FakePage()
    page.url = "https://www.shine.com/myshine/resume/upload"
    page.body = "Upload Resume"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(ValueError, match="up to 5 MB"):
        browser.update_profile_resume(resume)

    assert not hasattr(page, "uploaded_file")


def test_hirist_profile_navigation_does_not_wait_for_domcontentloaded(
    tmp_path,
):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    page.url = "https://www.hirist.tech/candidate/profile"
    page.body = "Ooops! Looks like you've got lost. Go Home."
    browser = CandidatePlatformBrowser("hirist")
    browser.page = page

    with pytest.raises(RuntimeError, match="profile page is unavailable"):
        browser.update_profile_resume(resume)

    assert page.goto_arguments[1]["wait_until"] == "commit"
    assert not hasattr(page, "uploaded_file")


@pytest.mark.parametrize(
    "platform",
    ["foundit", "indeed", "shine", "hirist", "wellfound"],
)
def test_resume_platforms_have_independent_browser_routes(platform):
    browser = CandidatePlatformBrowser(platform)

    assert browser.pages == PLATFORM_PAGES[platform]


def test_platform_browser_accepts_configured_site_routes():
    browser = CandidatePlatformBrowser(
        "shine",
        platform_config={
            "login_url": "https://example.test/sign-in",
            "profile_url": "https://example.test/candidate",
            "profile_edit_url": "https://example.test/profile/edit",
        },
    )

    assert browser.pages == {
        "login": "https://example.test/sign-in",
        "profile": "https://example.test/candidate",
        "profile_edit": "https://example.test/profile/edit",
    }


def test_shine_session_verification_requires_resume_upload_page(tmp_path):
    page = FakePage()
    page.url = "https://www.shine.com/myshine/resume/upload"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page
    browser.context = FakeSessionContext()
    browser.session_state_path = tmp_path / "shine-session.json"

    browser.verify_shine_session()

    assert page.goto_arguments[0] == (
        "https://www.shine.com/myshine/resume/upload",
    )
    assert browser.session_state_path.is_file()


def test_shine_session_save_retries_navigation_during_storage_capture(
    tmp_path,
):
    class NavigatingPage(FakePage):
        def __init__(self):
            self.evaluations = 0

        def evaluate(self, script):
            self.evaluations += 1
            if self.evaluations < 3:
                raise PlaywrightError(
                    "Page.evaluate: Execution context was destroyed, "
                    "most likely because of a navigation"
                )
            return {"sessionKey": "sessionValue"}

    page = NavigatingPage()
    browser = CandidatePlatformBrowser("shine")
    browser.page = page
    browser.context = FakeSessionContext()
    browser.session_state_path = tmp_path / "shine-session.json"

    browser._save_shine_session()

    state = json.loads(browser.session_state_path.read_text(encoding="utf-8"))
    assert page.evaluations == 3
    assert state["cookies"][0]["name"] == "shine-session"
    assert state["session_storage"] == {"sessionKey": "sessionValue"}


def test_shine_session_save_preserves_previous_storage_on_navigation(
    tmp_path,
    caplog,
):
    class NavigatingPage(FakePage):
        def evaluate(self, script):
            raise PlaywrightError(
                "Page.evaluate: Execution context was destroyed, "
                "most likely because of a navigation"
            )

    state_path = tmp_path / "shine-session.json"
    state_path.write_text(
        json.dumps(
            {
                "cookies": [],
                "session_storage": {"sessionKey": "previousValue"},
            }
        ),
        encoding="utf-8",
    )
    browser = CandidatePlatformBrowser("shine")
    browser.page = NavigatingPage()
    browser.context = FakeSessionContext()
    browser.session_state_path = state_path

    browser._save_shine_session()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["session_storage"] == {"sessionKey": "previousValue"}
    assert state["cookies"][0]["name"] == "shine-session"
    assert "session storage was being saved" in caplog.text


def test_shine_session_verification_rejects_login_redirect():
    page = FakePage()
    page.url = "https://www.shine.com/myshine/login/?next=/myshine/resume/upload"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(RuntimeError, match="Shine sign-in was not verified"):
        browser.verify_shine_session()


def test_shine_profile_preparation_opens_profile_editor():
    page = FakePage()
    page.url = "https://www.shine.com/myshine/myprofile"
    page.reveal_update_button_after_wait = True
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    browser.prepare_profile_update()

    assert page.goto_arguments[0] == (
        "https://www.shine.com/myshine/myprofile",
    )
    assert page.goto_arguments[1]["wait_until"] == "domcontentloaded"
    assert page.profile_update_wait_timeout == 30000
    assert page.profile_update_button_count == 1


def test_shine_profile_preparation_rejects_login_redirect():
    page = FakePage()
    page.url = "https://www.shine.com/myshine/login/"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(
        RuntimeError,
        match="redirected to sign-in",
    ):
        browser.prepare_profile_update()


def test_shine_profile_preparation_reports_editor_load_timeout():
    page = FakePage()
    page.url = "https://www.shine.com/myshine/myprofile"
    browser = CandidatePlatformBrowser("shine")
    browser.page = page

    with pytest.raises(
        RuntimeError,
        match="Update button was not visible after 30 seconds",
    ):
        browser.prepare_profile_update()


def test_shine_session_state_restores_cookies_and_session_storage(tmp_path):
    state_path = tmp_path / "shine-session.json"
    state_path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "shine-session", "value": "test-cookie"}
                ],
                "session_storage": {
                    "auth-session": "secret-value",
                },
            }
        ),
        encoding="utf-8",
    )
    browser = CandidatePlatformBrowser(
        "shine",
        platform_config={"session_state_file": str(state_path)},
    )
    browser.context = FakeSessionContext()

    browser._restore_shine_session()

    assert browser.context.added_cookies == [
        {"name": "shine-session", "value": "test-cookie"}
    ]
    assert len(browser.context.init_scripts) == 1
    assert "https://www.shine.com" in browser.context.init_scripts[0]
    assert "auth-session" in browser.context.init_scripts[0]


def test_shine_session_state_rejects_malformed_json(tmp_path):
    state_path = tmp_path / "shine-session.json"
    state_path.write_text("{", encoding="utf-8")
    browser = CandidatePlatformBrowser(
        "shine",
        platform_config={"session_state_file": str(state_path)},
    )
    browser.context = FakeSessionContext()

    with pytest.raises(RuntimeError, match="Could not read the saved Shine"):
        browser._restore_shine_session()


def test_shine_session_verification_is_platform_specific():
    browser = CandidatePlatformBrowser("hirist")
    browser.page = FakePage()

    with pytest.raises(ValueError, match="only implemented for Shine"):
        browser.verify_shine_session()


def test_platform_browser_stops_playwright_if_context_close_is_interrupted():
    class InterruptedContext:
        def close(self):
            raise KeyboardInterrupt

    class FakePlaywright:
        stopped = False

        def stop(self):
            self.stopped = True

    browser = CandidatePlatformBrowser("shine")
    playwright = FakePlaywright()
    browser.context = InterruptedContext()
    browser.playwright = playwright
    browser._owns_playwright = True

    with pytest.raises(KeyboardInterrupt):
        browser.close()

    assert playwright.stopped
    assert browser.context is None
    assert browser.playwright is None
    assert browser._owns_playwright is False


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


def test_profile_updater_supports_shine_state(tmp_path):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    updater = PlatformProfileUpdater(
        "shine",
        tmp_path / "shine-profile-state.json",
    )

    assert updater.is_current(resume) is False


def test_shine_skills_are_deduplicated_without_truncating_names():
    assert CandidatePlatformBrowser._clean_shine_skills(
        ["Linux", "Python", " linux ", "", None]
    ) == ["Linux", "Python"]
    assert CandidatePlatformBrowser._normalize_shine_skill("Linux ×") == (
        "linux"
    )


def test_shine_total_experience_only_accepts_supported_year_values():
    assert (
        CandidatePlatformBrowser._shine_total_experience_value("5 years")
        == "5 Yrs"
    )
    assert (
        CandidatePlatformBrowser._shine_total_experience_value(
            "2 years 6 months"
        )
        is None
    )


def test_shine_current_employment_requires_one_explicit_current_role():
    assert CandidatePlatformBrowser._shine_current_employment(
        [{"company": "Example", "is_current": True}]
    ) == {"company": "Example", "is_current": True}
    assert CandidatePlatformBrowser._shine_current_employment(
        [{"company": "Example", "is_current": False}]
    ) == {}

    with pytest.raises(ValueError, match="multiple current roles"):
        CandidatePlatformBrowser._shine_current_employment(
            [
                {"company": "Example A", "is_current": True},
                {"company": "Example B", "is_current": True},
            ]
        )


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
