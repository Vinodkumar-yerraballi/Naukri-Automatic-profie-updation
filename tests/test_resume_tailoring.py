import json
from urllib.error import HTTPError

import pytest
from docx import Document

from src.profile import resume_tailoring
from src.profile.resume_tailoring import ResumeTailoringService


class FakeResumeTailoringService(ResumeTailoringService):
    def _request_completion(self, prompt):
        assert "do not invent" in prompt.lower()
        assert "Data Analyst" in prompt
        return "## Summary\nExperienced analyst.\n\n- Python\n- SQL"


def test_create_draft_writes_job_specific_docx(tmp_path):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text(
        "Vinod Kumar\nSkills: Python, SQL", encoding="utf-8"
    )
    output_directory = tmp_path / "drafts"
    service = FakeResumeTailoringService(
        resume_path=resume_path,
        output_directory=output_directory,
    )

    output_path = service.create_draft(
        {
            "title": "Data Analyst",
            "company": "Example Co",
            "location": "Bengaluru",
            "job_url": "https://example.invalid/jobs/123",
            "description": "Use Python and SQL for reporting.",
        }
    )

    assert output_path.is_file()
    paragraphs = [
        paragraph.text for paragraph in Document(output_path).paragraphs
    ]
    assert any("AI-assisted draft" in paragraph for paragraph in paragraphs)
    assert any("Experienced analyst." in paragraph for paragraph in paragraphs)
    assert any(paragraph == "Python" for paragraph in paragraphs)


def test_create_draft_requires_description(tmp_path):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = FakeResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
    )

    try:
        service.create_draft({"title": "Data Analyst"})
    except ValueError as error:
        assert "job description" in str(error)
    else:
        raise AssertionError("A description-less job should be rejected.")


def test_create_draft_falls_back_to_local_provider(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
        fallback_provider="ollama",
    )
    monkeypatch.setattr(
        service,
        "_request_completion",
        lambda prompt: (_ for _ in ()).throw(
            RuntimeError("Gemini timed out")
        ),
    )
    monkeypatch.setattr(
        service.fallback_service,
        "_request_completion",
        lambda prompt: "Local resume draft",
    )

    output_path = service.create_draft(
        {
            "title": "Data Analyst",
            "company": "Example Co",
            "job_url": "https://example.invalid/jobs/123",
            "description": "Use Python and SQL.",
        }
    )

    assert output_path.is_file()
    assert service.fallback_service.provider == "ollama"


def test_complete_prompt_falls_back_when_primary_provider_fails(
    tmp_path,
    monkeypatch,
):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
        fallback_provider="ollama",
    )
    primary_calls = []
    fallback_calls = []

    def fail_primary(prompt):
        primary_calls.append(prompt)
        raise RuntimeError("Gemini request failed with HTTP 503")

    def complete_with_fallback(prompt):
        fallback_calls.append(prompt)
        return '{"skills": ["Python"]}'

    monkeypatch.setattr(service, "_request_completion", fail_primary)
    monkeypatch.setattr(
        service.fallback_service,
        "_request_completion",
        complete_with_fallback,
    )

    result = service.complete_prompt("Extract profile facts")

    assert result == '{"skills": ["Python"]}'
    assert primary_calls == ["Extract profile facts"]
    assert fallback_calls == ["Extract profile facts"]


def test_complete_prompt_reports_primary_and_fallback_failures(
    tmp_path,
    monkeypatch,
):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
        fallback_provider="ollama",
    )
    monkeypatch.setattr(
        service,
        "_request_completion",
        lambda prompt: (_ for _ in ()).throw(
            RuntimeError("Gemini HTTP 503")
        ),
    )
    monkeypatch.setattr(
        service.fallback_service,
        "_request_completion",
        lambda prompt: (_ for _ in ()).throw(
            RuntimeError("Ollama is unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="Both gemini and ollama"):
        service.complete_prompt("Extract profile facts")


def test_ollama_completion_uses_local_api_without_api_key(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        provider="ollama",
    )
    calls = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"message": {"content": "Tailored resume"}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls["url"] = request.full_url
        calls["headers"] = request.headers
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)

    result = service._request_completion("Make a resume draft")

    assert result == "Tailored resume"
    assert calls["url"] == "http://localhost:11434/api/chat"
    assert calls["payload"]["model"] == "qwen3:8b"
    assert calls["payload"]["stream"] is False
    assert "X-api-key" not in calls["headers"]


def test_gemini_completion_uses_api_key_header(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
        model="gemini-3.8-flash",
    )
    calls = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Tailored Gemini resume"}]
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls["url"] = request.full_url
        calls["headers"] = request.headers
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)

    result = service._request_completion("Make a resume draft")

    assert result == "Tailored Gemini resume"
    assert calls["url"].endswith(
        "/models/gemini-3.8-flash:generateContent"
    )
    assert calls["headers"]["X-goog-api-key"] == "test-gemini-key"
    assert calls["payload"]["system_instruction"]["parts"]


def test_gemini_retries_temporary_server_failure(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
    )
    attempts = []
    sleeps = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "Resume draft"}]}}
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        attempts.append(request.full_url)
        if len(attempts) == 1:
            raise HTTPError(
                request.full_url, 503, "Service Unavailable", {}, None
            )
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)
    monkeypatch.setattr(resume_tailoring.time, "sleep", sleeps.append)

    result = service._request_completion("Make a resume draft")

    assert result == "Resume draft"
    assert len(attempts) == 2
    assert sleeps == [1]


def test_gemini_retries_timeout(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
    )
    attempts = []
    timeouts = []
    sleeps = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "Resume draft"}]}}
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        attempts.append(request.full_url)
        timeouts.append(timeout)
        if len(attempts) == 1:
            raise TimeoutError("read timed out")
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)
    monkeypatch.setattr(resume_tailoring.time, "sleep", sleeps.append)

    result = service._request_completion("Make a resume draft")

    assert result == "Resume draft"
    assert len(attempts) == 2
    assert timeouts == [180, 180]
    assert sleeps == [1]


def test_gemini_reports_persistent_server_failure(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
    )
    attempts = []

    def fail_with_503(request, timeout):
        attempts.append(request.full_url)
        raise HTTPError(
            request.full_url, 503, "Service Unavailable", {}, None
        )

    monkeypatch.setattr(
        resume_tailoring,
        "urlopen",
        fail_with_503,
    )
    monkeypatch.setattr(resume_tailoring.time, "sleep", lambda seconds: None)

    try:
        service._request_completion("Make a resume draft")
    except RuntimeError as error:
        assert "HTTP 503" in str(error)
    else:
        raise AssertionError("Persistent server errors should be reported.")

    assert len(attempts) == 3


def test_gemini_provider_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    try:
        ResumeTailoringService.from_config(
            {
                "enabled": True,
                "provider": "gemini",
                "resume_path": str(tmp_path / "missing-resume.txt"),
            }
        )
    except RuntimeError as error:
        assert "GEMINI_API_KEY" in str(error)
    else:
        raise AssertionError("Gemini setup should require an API key.")


def test_gemini_provider_loads_key_from_local_dotenv(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=test-key-from-dotenv\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    service = ResumeTailoringService.from_config(
        {
            "enabled": True,
            "provider": "gemini",
            "resume_path": str(resume_path),
        }
    )

    assert service is not None
    assert service.api_key == "test-key-from-dotenv"
