import io
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


def test_anthropic_provider_loads_key_from_environment(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "ANTHROPIC_API_KEY=test-anthropic-key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    service = ResumeTailoringService.from_config(
        {
            "enabled": True,
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "resume_path": str(resume_path),
            "output_directory": str(tmp_path / "drafts"),
        }
    )

    assert service is not None
    assert service.provider == "anthropic"
    assert service.api_key == "test-anthropic-key"
    assert service.model == "claude-sonnet-4-5"


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
    assert calls["payload"]["think"] is False
    assert calls["payload"]["options"]["num_predict"] == 2048
    assert "X-api-key" not in calls["headers"]


def test_ollama_json_completion_requests_json_mode(tmp_path, monkeypatch):
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
                {"message": {"content": '{"skills": ["Python"]}'}}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)

    result = service.complete_prompt(
        "Extract resume facts",
        response_format="json",
    )

    assert result == '{"skills": ["Python"]}'
    assert calls["payload"]["format"] == "json"
    assert calls["payload"]["options"]["num_predict"] == 512


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
    assert "responseMimeType" not in calls["payload"]["generationConfig"]


def test_gemini_json_completion_requests_json_mime_type(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-gemini-key",
        provider="gemini",
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
                        {"content": {"parts": [{"text": "{}"}]}}
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)

    service.complete_prompt("Extract resume facts", response_format="json")

    assert (
        calls["payload"]["generationConfig"]["responseMimeType"]
        == "application/json"
    )


def test_groq_json_completion_uses_chat_completions_api(
    tmp_path,
    monkeypatch,
):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key="test-groq-key",
        provider="groq",
        model="openai/gpt-oss-120b",
    )
    calls = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": '{"skills": ["SQL"]}'}}]}
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls["url"] = request.full_url
        calls["authorization"] = request.get_header("Authorization")
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(resume_tailoring, "urlopen", fake_urlopen)

    result = service.complete_prompt(
        "Extract resume facts",
        response_format="json",
    )

    assert result == '{"skills": ["SQL"]}'
    assert calls["url"] == ResumeTailoringService.GROQ_API_URL
    assert calls["authorization"] == "Bearer test-groq-key"
    assert calls["payload"]["model"] == "openai/gpt-oss-120b"
    assert calls["payload"]["response_format"] == {"type": "json_object"}


def test_groq_provider_loads_key_from_local_dotenv(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "GROQ_API_KEY=test-groq-key\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    service = ResumeTailoringService.from_config(
        {
            "enabled": True,
            "provider": "groq",
            "resume_path": str(resume_path),
        }
    )

    assert service is not None
    assert service.provider == "groq"
    assert service.api_key == "test-groq-key"
    assert service.model == "openai/gpt-oss-120b"


def test_groq_provider_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ResumeTailoringService.from_config(
            {
                "enabled": True,
                "provider": "groq",
                "resume_path": str(tmp_path / "missing-resume.txt"),
            }
        )


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
    assert timeouts == [60, 60]
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

    assert len(attempts) == 2


def test_provider_http_error_includes_detail_without_api_key(
    tmp_path,
    monkeypatch,
):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    secret = "secret-gemini-api-key"
    service = ResumeTailoringService(
        resume_path=resume_path,
        output_directory=tmp_path / "drafts",
        api_key=secret,
        provider="gemini",
    )

    def fail_with_bad_request(request, timeout):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},
            io.BytesIO(
                json.dumps(
                    {
                        "error": {
                            "message": f"Invalid model; token was {secret}"
                        }
                    }
                ).encode("utf-8")
            ),
        )

    monkeypatch.setattr(resume_tailoring, "urlopen", fail_with_bad_request)

    with pytest.raises(RuntimeError) as error:
        service._request_completion("Make a resume draft")

    assert "Invalid model" in str(error.value)
    assert secret not in str(error.value)


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


def test_ollama_fallback_model_can_be_overridden_separately(
    tmp_path,
    monkeypatch,
):
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Python and SQL", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=test-gemini-key\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("OLLAMA_FALLBACK_MODEL", "qwen3:1.7b")

    service = ResumeTailoringService.from_config(
        {
            "enabled": True,
            "provider": "gemini",
            "fallback_provider": "ollama",
            "fallback_model": "qwen3:8b",
            "resume_path": str(resume_path),
        }
    )

    assert service is not None
    assert service.fallback_service is not None
    assert service.fallback_service.model == "qwen3:1.7b"
