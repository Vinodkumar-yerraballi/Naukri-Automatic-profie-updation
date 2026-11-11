import json
from datetime import date, timedelta

import pytest

import main
from src.profile.profile_text_proposal import ProfileTextProposal


class FakeAIService:
    resume_path = "data/resume.pdf"
    resume_text = "Python and SQL analytics projects."

    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def complete_prompt(self, prompt, response_format=None):
        assert response_format == "json"
        self.prompts.append(prompt)
        return next(self.responses)


PROMPTS = {
    "headline_prompt": "Mention relevant data skills.",
    "about_prompt": "Keep it concise.",
}


def response(headline, about="Resume-supported profile summary."):
    return json.dumps({"headline": headline, "about": about})


def test_generates_new_daily_headline_and_retains_history(tmp_path):
    history_path = tmp_path / "history.json"
    ai_service = FakeAIService(
        [
            response("Data Analyst | Python and SQL"),
            response("Analytics Professional | Python & SQL"),
        ]
    )
    generator = ProfileTextProposal(ai_service, history_path)
    first_day = date(2026, 11, 11)

    first_path = generator.generate(
        "naukri",
        PROMPTS,
        tmp_path / "proposals",
        today=first_day,
    )
    second_path = generator.generate(
        "naukri",
        PROMPTS,
        tmp_path / "proposals",
        today=first_day + timedelta(days=1),
    )

    assert first_path.is_file()
    assert second_path.is_file()
    assert json.loads(first_path.read_text(encoding="utf-8"))[
        "review_required"
    ]
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history["naukri"]) == 2
    assert "Data Analyst | Python and SQL" in ai_service.prompts[1]


def test_same_day_is_idempotent(tmp_path):
    ai_service = FakeAIService([response("Data analyst")])
    generator = ProfileTextProposal(
        ai_service,
        tmp_path / "history.json",
    )
    kwargs = {
        "platform": "naukri",
        "prompts": PROMPTS,
        "output_directory": tmp_path / "proposals",
        "today": date(2026, 11, 11),
    }

    first_path = generator.generate(**kwargs)
    second_path = generator.generate(**kwargs)

    assert first_path == second_path
    assert len(ai_service.prompts) == 1


def test_retries_duplicate_headline_ignoring_punctuation(tmp_path):
    ai_service = FakeAIService(
        [
            response("Data Analyst!"),
            response("data analyst"),
            response("SQL Analytics Professional"),
        ]
    )
    generator = ProfileTextProposal(
        ai_service,
        tmp_path / "history.json",
    )
    generator.generate(
        "naukri",
        PROMPTS,
        tmp_path / "proposals",
        today=date(2026, 11, 11),
    )
    generator.generate(
        "naukri",
        PROMPTS,
        tmp_path / "proposals",
        today=date(2026, 11, 12),
    )

    assert len(ai_service.prompts) == 3
    assert "repeated an earlier one" in ai_service.prompts[2]


def test_rejects_repeated_headline_after_retry_limit(tmp_path):
    ai_service = FakeAIService([response("Same headline")] * 4)
    generator = ProfileTextProposal(
        ai_service,
        tmp_path / "history.json",
    )
    generator.generate(
        "naukri",
        PROMPTS,
        tmp_path / "proposals",
        today=date(2026, 11, 11),
    )

    with pytest.raises(RuntimeError, match="repeated a previously used"):
        generator.generate(
            "naukri",
            PROMPTS,
            tmp_path / "proposals",
            today=date(2026, 11, 12),
        )

    assert not (tmp_path / "proposals" / "naukri_2026-11-12.json").exists()


def test_rejects_empty_or_unstructured_ai_response(tmp_path):
    ai_service = FakeAIService(['{"headline": "", "about": "Summary"}'])
    generator = ProfileTextProposal(
        ai_service,
        tmp_path / "history.json",
    )

    with pytest.raises(ValueError, match="non-empty"):
        generator.generate(
            "naukri",
            PROMPTS,
            tmp_path / "proposals",
            today=date(2026, 11, 11),
        )


def test_command_uses_platform_resume_and_configured_paths(
    monkeypatch,
    tmp_path,
):
    observed = {}

    class ConfigManager:
        def get_profile_text_config(self):
            return {
                "enabled": True,
                "history_file": str(tmp_path / "history.json"),
                "output_directory": str(tmp_path / "proposals"),
                "platforms": {"foundit": PROMPTS},
            }

        def get_naukri_profile_config(self):
            return {}

        def get_resume_platform_configs(self):
            return {"foundit": {"resume_path": "data/foundit.pdf"}}

        def get_resume_tailoring_config(self):
            return {"enabled": True, "resume_path": "data/resume.pdf"}

    class ResumeTailoringService:
        @classmethod
        def from_config(cls, config):
            observed["service_config"] = config
            return object()

    class Proposal:
        def __init__(self, ai_service, history_path):
            observed["history_path"] = history_path

        def generate(self, platform, prompts, output_directory):
            observed["generation"] = (
                platform,
                prompts,
                output_directory,
            )
            return tmp_path / "proposal.json"

    monkeypatch.setattr(main, "ConfigManager", ConfigManager)
    monkeypatch.setattr(main, "ResumeTailoringService", ResumeTailoringService)
    monkeypatch.setattr(main, "ProfileTextProposal", Proposal)

    main.generate_profile_text("foundit")

    assert observed["service_config"]["resume_path"] == "data/foundit.pdf"
    assert observed["history_path"] == str(tmp_path / "history.json")
    assert observed["generation"] == (
        "foundit",
        PROMPTS,
        str(tmp_path / "proposals"),
    )


def test_apply_profile_text_requires_confirmation_and_records_success(
    monkeypatch,
    tmp_path,
):
    proposal_path = tmp_path / "naukri_2026-11-11.json"
    proposal_path.write_text(
        json.dumps(
            {
                "platform": "naukri",
                "created_on": "2026-11-11",
                "headline": "Data Analyst | Python and SQL",
                "about": "Reviewed About text.",
                "review_required": True,
                "applied": False,
            }
        ),
        encoding="utf-8",
    )
    observed = {}

    class ConfigManager:
        def get_profile_text_config(self):
            return {"output_directory": str(tmp_path)}

        def get_naukri_profile_config(self):
            return {"browser_profile_directory": "data/naukri_browser_profile"}

    class NaukriBrowser:
        def __init__(self, headless):
            assert headless is False

        def start_persistent(self, profile_directory):
            observed["profile_directory"] = profile_directory

        def update_profile_fields(self, proposal):
            observed["proposal"] = proposal
            return ["headline"]

        def close(self):
            observed["closed"] = True

    monkeypatch.setattr(main, "ConfigManager", ConfigManager)
    monkeypatch.setattr(main, "NaukriBrowser", NaukriBrowser)
    monkeypatch.setattr("builtins.input", lambda prompt: "APPLY")

    main.apply_profile_text("naukri")

    saved_proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    assert observed["proposal"] == {
        "sections": ["headline"],
        "data": {"headline": "Data Analyst | Python and SQL"},
    }
    assert observed["closed"] is True
    assert saved_proposal["applied"] is True
    assert saved_proposal["applied_fields"] == ["headline"]


def test_apply_profile_text_decline_does_not_open_browser(
    monkeypatch,
    tmp_path,
):
    proposal_path = tmp_path / "naukri_2026-11-11.json"
    proposal_path.write_text(
        json.dumps(
            {
                "platform": "naukri",
                "headline": "Data Analyst | Python and SQL",
                "applied": False,
            }
        ),
        encoding="utf-8",
    )

    class ConfigManager:
        def get_profile_text_config(self):
            return {"output_directory": str(tmp_path)}

    monkeypatch.setattr(main, "ConfigManager", ConfigManager)
    monkeypatch.setattr("builtins.input", lambda prompt: "no")

    main.apply_profile_text("naukri")

    saved_proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    assert saved_proposal["applied"] is False


@pytest.mark.parametrize("platform", ["foundit", "wellfound"])
def test_apply_profile_text_rejects_unsupported_platform(platform):
    with pytest.raises(
        RuntimeError,
        match="not implemented",
    ):
        main.apply_profile_text(platform)
