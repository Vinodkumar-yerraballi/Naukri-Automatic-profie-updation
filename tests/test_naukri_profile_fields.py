from src.ingestion.naukri_browser import NaukriBrowser


class FakeSuggestion:
    def __init__(self, text):
        self.text = text

    def is_visible(self):
        return True

    def inner_text(self):
        return self.text


class FakeSuggestions:
    def __init__(self, suggestions):
        self.suggestions = suggestions

    def all(self):
        return self.suggestions


class FakePage:
    def __init__(self, suggestions):
        self.suggestions = suggestions

    def locator(self, selector):
        assert selector == "li, [role='option'], .sWrap .chip, .suggestor-box li"
        return FakeSuggestions(self.suggestions)


def test_naukri_skill_normalization_ignores_chip_remove_icon_and_spacing():
    assert NaukriBrowser._normalize_naukri_skill("  Data   Engineering × ") == (
        "data engineering"
    )


def test_naukri_exact_suggestion_matches_skill_chip_with_remove_icon():
    browser = NaukriBrowser()
    suggestion = FakeSuggestion("Data Engineering\n×")
    browser.page = FakePage([suggestion])

    assert browser._naukri_exact_suggestion("Data Engineering") is suggestion
