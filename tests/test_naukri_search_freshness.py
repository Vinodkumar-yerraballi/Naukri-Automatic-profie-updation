from src.ingestion.naukri_browser import NaukriBrowser


class FakePage:
    url = "https://www.naukri.com/data-analyst-jobs-in-bangalore"

    def __init__(self):
        self.goto_url = None

    def goto(self, url, **kwargs):
        self.goto_url = url

    def wait_for_timeout(self, timeout):
        pass

    def title(self):
        return "Job search"


def test_search_jobs_requests_last_day_filter():
    browser = NaukriBrowser()
    browser.page = FakePage()

    browser.search_jobs(
        role="Data Analyst",
        location="Bangalore",
        posted_within_hours=24,
    )

    assert browser.page.goto_url.endswith("?jobAge=1")


def test_search_jobs_can_run_without_age_filter():
    browser = NaukriBrowser()
    browser.page = FakePage()

    browser.search_jobs(role="Data Analyst", location="Bangalore")

    assert "?" not in browser.page.goto_url
