import builtins

import main


def test_profile_proposal_requires_exact_apply_confirmation(
    monkeypatch,
    capsys,
    tmp_path,
):
    proposal = {"data": {"skills": ["SQL"]}}
    monkeypatch.setattr(builtins, "input", lambda prompt: "NO")

    assert main._confirm_profile_proposal(
        "foundit",
        tmp_path / "proposal.json",
        proposal,
    ) is False
    assert "Profile fields were not changed." in capsys.readouterr().out

    monkeypatch.setattr(builtins, "input", lambda prompt: " APPLY ")
    assert main._confirm_profile_proposal(
        "foundit",
        tmp_path / "proposal.json",
        proposal,
    ) is True


def test_profile_proposal_is_reused_for_an_unchanged_source_resume(
    tmp_path,
):
    resume = tmp_path / "resume.txt"
    resume.write_text("Skills: SQL", encoding="utf-8")
    proposal_path = tmp_path / "proposal.json"

    class AIService:
        resume_path = resume
        resume_text = "Skills: SQL"
        calls = 0

        def complete_prompt(self, prompt, response_format=None):
            self.calls += 1
            assert response_format == "json"
            return '{"skills": ["SQL"]}'

    ai_service = AIService()
    first = main._create_or_load_profile_proposal(
        ai_service,
        ["skills"],
        proposal_path,
    )
    second = main._create_or_load_profile_proposal(
        ai_service,
        ["skills"],
        proposal_path,
    )

    assert first["source_resume_sha256"]
    assert second == first
    assert ai_service.calls == 1
