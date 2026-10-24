import re

import pytest

from src.ingestion.naukri_browser import NaukriBrowser


class FakeLocator:
    def __init__(self, page, role=None, name=None, visible=True):
        self.page = page
        self.role = role
        self.name = name
        self.visible = visible

    def count(self):
        if self.role:
            return int(self.page.has_action(self.role, self.name))
        return 1

    def nth(self, index):
        assert index == 0
        return self

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return True

    def click(self, timeout):
        self.page.on_apply()

    def inner_text(self):
        return self.page.text


class FakePage:
    def __init__(self, text="", apply_available=True, after_apply=""):
        self.text = text
        self.url = "https://www.naukri.com/job-listing"
        self.apply_available = apply_available
        self.after_apply = after_apply

    def goto(self, url, **kwargs):
        self.url = url

    def wait_for_timeout(self, milliseconds):
        pass

    def locator(self, selector):
        return FakeLocator(self)

    def has_action(self, role, name):
        pattern = name if isinstance(name, re.Pattern) else re.compile(name)
        if pattern.fullmatch("Applied"):
            return (
                role == "button"
                and "already applied" in self.text.lower()
            )
        if pattern.fullmatch("Apply"):
            return role == "button" and self.apply_available
        return False

    def get_by_role(self, role, name):
        return FakeLocator(self, role, name)

    def on_apply(self):
        self.text = self.after_apply


def test_submit_application_returns_success_only_after_confirmation():
    browser = NaukriBrowser()
    browser.page = FakePage(
        text="Data Analyst",
        after_apply="Data Analyst - You have successfully applied",
    )

    result = browser.submit_application(
        {
            "job_url": "https://www.naukri.com/job-listing",
            "title": "Data Analyst",
        }
    )

    assert result["status"] == "APPLIED"


def test_submit_application_fails_closed_without_confirmation():
    browser = NaukriBrowser()
    browser.page = FakePage(
        text="Data Analyst",
        after_apply="Please complete your profile",
    )

    result = browser.submit_application(
        {
            "job_url": "https://www.naukri.com/job-listing",
            "title": "Data Analyst",
        }
    )

    assert result["status"] == "UNCONFIRMED"


def test_submit_application_requires_single_supported_apply_action():
    browser = NaukriBrowser()
    browser.page = FakePage(text="Data Analyst", apply_available=False)

    result = browser.submit_application(
        {
            "job_url": "https://www.naukri.com/job-listing",
            "title": "Data Analyst",
        }
    )

    assert result["status"] == "MANUAL_ACTION_REQUIRED"


def test_submit_application_does_not_repeat_an_existing_application():
    browser = NaukriBrowser()
    browser.page = FakePage(text="Data Analyst - You have already applied")

    result = browser.submit_application(
        {
            "job_url": "https://www.naukri.com/job-listing",
            "title": "Data Analyst",
        }
    )

    assert result["status"] == "ALREADY_APPLIED"


def test_submit_application_refuses_a_mismatched_job_title():
    browser = NaukriBrowser()
    browser.page = FakePage(text="Different job title")

    result = browser.submit_application(
        {
            "job_url": "https://www.naukri.com/job-listing",
            "title": "Data Analyst",
        }
    )

    assert result["status"] == "MANUAL_ACTION_REQUIRED"


def test_submit_application_refuses_non_naukri_urls():
    browser = NaukriBrowser()
    browser.page = FakePage()

    with pytest.raises(ValueError, match="outside naukri.com"):
        browser.submit_application(
            {
                "job_url": "https://example.com/job",
                "title": "Data Analyst",
            }
        )
