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

    def wait_for_timeout(self, timeout):
        pass


class FakeTypingField:
    def __init__(self, maxlength):
        self.maxlength = maxlength
        self.calls = []

    def get_attribute(self, name):
        assert name == "maxlength"
        return self.maxlength

    def fill(self, value):
        self.calls.append(("fill", value))

    def press_sequentially(self, value, delay):
        self.calls.append(("type", value, delay))


class FakeTextLocator:
    def __init__(self, text):
        self.text = text

    def count(self):
        return 1

    def inner_text(self):
        return self.text


class FakeEmploymentRow:
    def __init__(self, title, company, dates):
        self.fields = {
            ".emp-desg": FakeTextLocator(title),
            ".emp-org": FakeTextLocator(company),
            ".experienceType": FakeTextLocator(dates),
        }

    def locator(self, selector):
        return self.fields[selector]


class FakeEditorButton:
    def __init__(self, visible):
        self.visible = visible
        self.clicked = False

    def is_visible(self):
        return self.visible

    def wait_for(self, state, timeout):
        assert state == "visible"

    def click(self, timeout):
        self.clicked = True


class FakeEditorButtons:
    def __init__(self, buttons):
        self.buttons = buttons
        self.first = buttons[0]

    def count(self):
        return len(self.buttons)

    def nth(self, index):
        return self.buttons[index]


class FakeEditorPage:
    def __init__(self, buttons):
        self.buttons = FakeEditorButtons(buttons)

    def get_by_role(self, role, name):
        assert role == "button"
        assert name == "Edit key skills"
        return self.buttons

    def wait_for_timeout(self, timeout):
        pass


class FakeScopedSuggestionPage:
    def __init__(self, suggestions):
        self.suggestions = suggestions

    def locator(self, selector):
        assert selector == "#skill-suggestions li, #skill-suggestions [role='option']"
        return FakeSuggestions(self.suggestions)


class FakeSuggestionField:
    def get_attribute(self, name):
        assert name == "aria-controls"
        return "skill-suggestions"


def test_naukri_skill_normalization_ignores_chip_remove_icon_and_spacing():
    assert NaukriBrowser._normalize_naukri_skill("  Data   Engineering × ") == (
        "data engineering"
    )


def test_naukri_skill_normalization_ignores_live_chip_remove_label():
    assert NaukriBrowser._normalize_naukri_skill("PythonCross") == "python"


def test_naukri_exact_suggestion_matches_skill_chip_with_remove_icon():
    browser = NaukriBrowser()
    suggestion = FakeSuggestion("Data Engineering\n×")
    browser.page = FakePage([suggestion])

    assert browser._naukri_exact_suggestion("Data Engineering") is suggestion


def test_naukri_exact_suggestion_is_scoped_to_the_active_input():
    browser = NaukriBrowser()
    suggestion = FakeSuggestion("Python")
    browser.page = FakeScopedSuggestionPage([suggestion])

    assert browser._naukri_exact_suggestion(
        "Python",
        FakeSuggestionField(),
    ) is suggestion


def test_naukri_editor_uses_the_single_visible_control():
    hidden = FakeEditorButton(False)
    visible = FakeEditorButton(True)
    browser = NaukriBrowser()
    browser.page = FakeEditorPage([hidden, visible])

    browser._open_naukri_editor("Edit key skills")

    assert not hidden.clicked
    assert visible.clicked


def test_naukri_skill_search_types_a_prefix_to_open_suggestions():
    browser = NaukriBrowser()
    browser.page = FakePage([])
    field = FakeTypingField("5")

    browser._type_naukri_suggestion_query(field, "Python")

    assert field.calls == [("fill", ""), ("type", "Pytho", 35)]


def test_naukri_skill_search_limits_long_input_to_five_characters():
    browser = NaukriBrowser()
    browser.page = FakePage([])
    field = FakeTypingField("100")

    browser._type_naukri_suggestion_query(field, "Data Engineering")

    assert field.calls == [("fill", ""), ("type", "Data", 35)]


def test_naukri_date_parts_extracts_only_resume_supported_parts():
    assert NaukriBrowser._naukri_date_parts("Feb 2020") == ("2020", "Feb")
    assert NaukriBrowser._naukri_date_parts("2020") == ("2020", None)
    assert NaukriBrowser._naukri_date_parts(None) == (None, None)


def test_naukri_employment_matching_avoids_existing_resume_record_duplicates():
    row = FakeEmploymentRow(
        "Associate Data Crawling",
        "Rubick.AI",
        "Full-time\nAug 2026 to Present",
    )

    assert NaukriBrowser._naukri_employment_matches(
        "Associate Data Crawling (AI Data Pipelines)",
        "Rubick.AI",
        "Aug 2026",
        row,
    )


def test_naukri_employment_matching_requires_the_same_company_and_start_date():
    row = FakeEmploymentRow(
        "Associate Data Crawling",
        "Rubick.AI",
        "Full-time\nAug 2026 to Present",
    )

    assert not NaukriBrowser._naukri_employment_matches(
        "Associate Data Crawling",
        "Different Company",
        "Aug 2026",
        row,
    )
    assert not NaukriBrowser._naukri_employment_matches(
        "Associate Data Crawling",
        "Rubick.AI",
        "Jan 2024",
        row,
    )


def test_naukri_profile_update_respects_selected_sections(monkeypatch):
    class FakePage:
        url = "https://www.naukri.com/mnjuser/profile"

        def goto(self, *args, **kwargs):
            pass

        def wait_for_timeout(self, timeout):
            pass

    browser = NaukriBrowser()
    browser.page = FakePage()
    browser.detect_security_challenge = lambda: False
    called = []

    def updater(name):
        def update(value):
            called.append(name)
            return True

        return update

    browser._update_naukri_headline = updater("headline")
    browser._update_naukri_skills = updater("skills")
    browser._update_naukri_employment = updater("employment")
    browser._update_naukri_projects = updater("projects")

    changed = browser.update_profile_fields(
        {
            "sections": ["skills", "employment"],
            "data": {
                "headline": "Analyst",
                "skills": ["Python"],
                "employment": [],
                "projects": [{"title": "Project"}],
            },
        }
    )

    assert called == ["skills", "employment"]
    assert changed == ["skills", "employment"]
