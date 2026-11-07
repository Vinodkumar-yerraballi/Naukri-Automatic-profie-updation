import pytest

from src.ingestion.instahyre_browser import InstahyreBrowser


class FakeTextLocator:
    def __init__(self, text):
        self.text = text
        self.clicked = False

    def all(self):
        return [self]

    def all_inner_texts(self):
        return [self.text]

    def is_visible(self):
        return True

    def inner_text(self):
        return self.text

    def click(self, timeout):
        self.clicked = True


class FakeCard:
    def __init__(self, values, text, href):
        self.values = values
        self.text = text
        self.href = href

    def get_attribute(self, name):
        assert name == "href"
        return self.href

    def inner_text(self):
        return self.text

    def is_visible(self):
        return True

    def locator(self, selector):
        if selector == ".company-name":
            return FakeTextLocator(self.values["title"])
        text = self.values.get(selector, "")
        return FakeTextLocator(text) if text else FakeTextLocator("")


class FakeFilterField:
    def __init__(self):
        self.value = None

    def count(self):
        return 1

    def fill(self, value):
        self.value = value


class FakeOption(FakeTextLocator):
    pass


class FakeFilterPage:
    def __init__(self, options):
        self.options = options
        self.field = FakeFilterField()

    def locator(self, selector):
        if selector == InstahyreBrowser.FILTER_OPTIONS_SELECTOR:
            return FakeTextLocatorList(self.options)
        return self.field

    def wait_for_timeout(self, timeout):
        pass


class FakeTextLocatorList:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


def test_extracts_instahyre_listing_fields_and_absolute_url():
    card = FakeCard(
        {
            ".employer-job-name": "Example Analytics - Data Analyst",
            ".employer-chips-location": "Bangalore",
            ".job-skills": "SQL, Python",
        },
        "Data Analyst Example Analytics Bangalore SQL Python",
        "/job-123-data-analyst-at-example-analytics-bangalore/",
    )

    job = InstahyreBrowser()._extract_job_card(card)

    assert job == {
        "job_url": (
            "https://www.instahyre.com/"
            "job-123-data-analyst-at-example-analytics-bangalore/"
        ),
        "company": "Example Analytics",
        "title": "Data Analyst",
        "location": "Bangalore",
        "experience": "",
        "description": (
            "Data Analyst Example Analytics Bangalore SQL Python SQL, Python"
        ),
    }


def test_skips_listing_links_outside_instahyre():
    card = FakeCard({}, "Data Analyst", "https://example.com/job")

    assert InstahyreBrowser()._extract_job_card(card) is None


def test_select_filter_chooses_matching_visible_option():
    browser = InstahyreBrowser()
    browser.page = FakeFilterPage(
        [FakeOption("Data Analyst"), FakeOption("Data Scientist")]
    )

    browser._select_filter(
        "#skills-drop-select-job-search-selectized",
        "Data Analyst",
        "job title",
    )

    assert browser.page.field.value == "Data Analyst"
    assert browser.page.options[0].clicked is True
    assert browser.page.options[1].clicked is False


def test_select_filter_reports_missing_site_option():
    browser = InstahyreBrowser()
    browser.page = FakeFilterPage([FakeOption("Data Engineer")])

    with pytest.raises(
        RuntimeError,
        match="did not offer 'Data Analyst'.*Data Engineer",
    ):
        browser._select_filter(
            "#skills-drop-select-job-search-selectized",
            "Data Analyst",
            "job title",
        )
