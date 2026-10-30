from src.ingestion.naukri_browser import NaukriBrowser


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector
        self.first = self

    def count(self):
        if self.selector == "body":
            return 1
        if self.selector == "input[type='file'][accept*='.pdf']":
            return 1
        if self.selector == (
            "input[type='button'][value*='resume' i], "
            "input[type='submit'][value*='resume' i], "
            "button[aria-label*='resume' i], "
            "button:has-text('resume')"
        ):
            return 1
        return 0

    def inner_text(self):
        return "resume.pdf"

    def set_input_files(self, path):
        self.page.uploaded_file = path

    def is_visible(self):
        return True

    def click(self, timeout):
        self.page.clicked_selector = self.selector


class FakePage:
    url = "https://www.naukri.com/mnjuser/profile"

    def locator(self, selector):
        return FakeLocator(self, selector)

    def goto(self, *args, **kwargs):
        pass

    def wait_for_timeout(self, timeout):
        pass

    def get_by_role(self, *args, **kwargs):
        raise AssertionError("Resume save controls must not use ambiguous roles")


def test_profile_resume_upload_clicks_resume_control_without_role_lookup(
    tmp_path,
):
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"candidate resume")
    page = FakePage()
    browser = NaukriBrowser()
    browser.page = page
    browser.detect_security_challenge = lambda: False

    browser.update_profile_resume(resume)

    assert page.uploaded_file == str(resume.resolve())
    assert page.clicked_selector.startswith("input[type='button']")


def test_persistent_session_reuses_initial_browser_tab(tmp_path, monkeypatch):
    class FakeContext:
        def __init__(self):
            self.initial_page = FakePage()
            self.pages = [self.initial_page]
            self.new_page_calls = 0

        def new_page(self):
            self.new_page_calls += 1
            return FakePage()

        def close(self):
            pass

    class FakeChromium:
        def __init__(self):
            self.context = FakeContext()

        def launch_persistent_context(self, **kwargs):
            return self.context

    class FakePlaywright:
        def __init__(self):
            self.chromium = FakeChromium()

        def stop(self):
            pass

    class FakePlaywrightManager:
        def __init__(self, playwright):
            self.playwright = playwright

        def start(self):
            return self.playwright

    playwright = FakePlaywright()
    monkeypatch.setattr(
        "src.ingestion.naukri_browser.sync_playwright",
        lambda: FakePlaywrightManager(playwright),
    )
    browser = NaukriBrowser()
    browser.start_persistent(tmp_path / "naukri_profile")

    assert browser.page is playwright.chromium.context.initial_page
    assert playwright.chromium.context.new_page_calls == 0
