import json

import pytest

from src.profile.resume_profile_proposal import ResumeProfileProposal


class FakeAIService:
    resume_path = "data/resume.pdf"
    resume_text = "Python and SQL; M.Sc. Applied Mathematics."

    def __init__(self, response):
        self.response = response
        self.prompt = None

    def _request_completion(self, prompt):
        self.prompt = prompt
        return self.response

    def complete_prompt(self, prompt):
        return self._request_completion(prompt)


def valid_profile():
    return {
        "headline": "Data Analyst skilled in Python and SQL",
        "summary": "Applied mathematics graduate with data analysis skills.",
        "skills": ["Python", "SQL"],
        "employment": [],
        "education": [
            {
                "qualification": "M.Sc.",
                "specialization": "Applied Mathematics",
                "institution": None,
                "start_year": None,
                "end_year": None,
            }
        ],
        "projects": [],
        "certifications": [],
    }


def test_create_proposal_limits_prompt_and_marks_review_required():
    ai_service = FakeAIService(json.dumps(valid_profile()))
    proposal_builder = ResumeProfileProposal(ai_service)

    proposal = proposal_builder.create(["headline", "education"])

    assert proposal["review_required"] is True
    assert proposal["unmatched_existing_records"] == "preserve"
    assert proposal["sections"] == ["education", "headline"]
    assert "phone numbers" in ai_service.prompt
    assert '"headline"' in ai_service.prompt


def test_create_profile_proposal_can_be_marked_for_automatic_update():
    proposal_builder = ResumeProfileProposal(
        FakeAIService(json.dumps(valid_profile()))
    )

    proposal = proposal_builder.create(
        ["skills", "employment", "projects"],
        review_required=False,
    )

    assert proposal["review_required"] is False


def test_create_proposal_rejects_unknown_section():
    proposal_builder = ResumeProfileProposal(
        FakeAIService(json.dumps(valid_profile()))
    )

    with pytest.raises(ValueError, match="Unsupported profile sections"):
        proposal_builder.create(["salary"])


def test_parse_response_rejects_unexpected_fields():
    data = valid_profile()
    data["phone"] = "not allowed"

    with pytest.raises(ValueError, match="unexpected field set"):
        ResumeProfileProposal._parse_response(json.dumps(data))


def test_parse_response_accepts_json_code_fence():
    proposal = ResumeProfileProposal._parse_response(
        "```json\n" + json.dumps(valid_profile()) + "\n```"
    )

    assert proposal["skills"] == ["Python", "SQL"]


def test_save_writes_reviewable_proposal_atomically(tmp_path):
    ai_service = FakeAIService(json.dumps(valid_profile()))
    proposal_builder = ResumeProfileProposal(ai_service)
    proposal = proposal_builder.create(["headline"])

    path = proposal_builder.save(proposal, tmp_path / "proposal.json")

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["review_required"] is True
    assert not path.with_suffix(".json.tmp").exists()
