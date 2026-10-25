from urllib.parse import parse_qs, urlparse

import pytest

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


def test_search_jobs_requests_experience_and_last_day_filters():
    browser = NaukriBrowser()
    browser.page = FakePage()

    browser.search_jobs(
        role="Data Analyst",
        location="Bangalore",
        posted_within_hours=24,
        experience={"minimum": 0, "maximum": 2},
    )

    query = parse_qs(urlparse(browser.page.goto_url).query)
    assert query == {"experience": ["0"], "jobAge": ["1"]}


def test_search_jobs_can_run_without_age_filter():
    browser = NaukriBrowser()
    browser.page = FakePage()

    browser.search_jobs(role="Data Analyst", location="Bangalore")

    assert "?" not in browser.page.goto_url


def test_search_jobs_rejects_invalid_experience_range():
    browser = NaukriBrowser()
    browser.page = FakePage()

    with pytest.raises(ValueError, match="experience must contain"):
        browser.search_jobs(
            role="Data Analyst",
            experience={"minimum": 3, "maximum": 2},
        )
