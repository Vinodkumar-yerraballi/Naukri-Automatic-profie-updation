import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from docx import Document
from dotenv import load_dotenv

from src.extraction.resume_parser import read_resume


class ResumeTailoringService:
    """Create factual, job-specific resume drafts using a configured AI."""

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        resume_path: str | Path,
        output_directory: str | Path,
        api_key: str | None = None,
        model: str = "qwen3:8b",
        provider: str = "ollama",
        base_url: str = "http://localhost:11434",
        fallback_provider: str | None = None,
        fallback_model: str = "qwen3:8b",
        fallback_base_url: str = "http://localhost:11434",
    ):
        self.provider = provider.lower()
        if self.provider not in {"anthropic", "ollama", "gemini"}:
            raise ValueError(
                "Resume provider must be 'anthropic', 'gemini', or 'ollama'."
            )
        if self.provider in {"anthropic", "gemini"} and not api_key:
            raise ValueError(f"An {self.provider.title()} API key is required.")
        self.resume_path = Path(resume_path)
        self.output_directory = Path(output_directory)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.resume_text = read_resume(self.resume_path)
        self.fallback_service = None
        if fallback_provider:
            if fallback_provider.lower() == self.provider:
                raise ValueError("Fallback provider must differ from primary.")
            self.fallback_service = ResumeTailoringService(
                resume_path=self.resume_path,
                output_directory=self.output_directory,
                model=fallback_model,
                provider=fallback_provider,
                base_url=fallback_base_url,
            )

    @classmethod
    def from_config(cls, config: dict) -> "ResumeTailoringService | None":
        if not config.get("enabled", False):
            return None
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
        provider = config.get("provider", "ollama").lower()
        api_key = None
        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Anthropic is selected, but ANTHROPIC_API_KEY is not set."
                )
        elif provider == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Gemini is selected, but GEMINI_API_KEY is not set."
                )
        elif provider != "ollama":
            raise ValueError(
                "Resume provider must be 'anthropic', 'gemini', or 'ollama'."
            )

        return cls(
            resume_path=config.get("resume_path", "data/resume.pdf"),
            output_directory=config.get(
                "output_directory", "data/processed/resumes"
            ),
            api_key=api_key,
            model=os.environ.get(
                {
                    "anthropic": "ANTHROPIC_MODEL",
                    "gemini": "GEMINI_MODEL",
                    "ollama": "OLLAMA_MODEL",
                }[provider],
                config.get(
                    "model",
                    "claude-sonnet-4-5"
                    if provider == "anthropic"
                    else "gemini-3.8-flash"
                    if provider == "gemini"
                    else "qwen3:8b",
                ),
            ),
            provider=provider,
            base_url=os.environ.get(
                "OLLAMA_BASE_URL", config.get("base_url", "http://localhost:11434")
            ),
            fallback_provider=config.get("fallback_provider"),
            fallback_model=os.environ.get(
                "OLLAMA_MODEL", config.get("fallback_model", "qwen3:8b")
            ),
            fallback_base_url=os.environ.get(
                "OLLAMA_BASE_URL",
                config.get(
                    "fallback_base_url", "http://localhost:11434"
                ),
            ),
        )

    def create_draft(self, job: dict) -> Path:
        description = (job.get("description") or job.get("job_description") or "").strip()
        if not description:
            raise ValueError("Cannot tailor a resume without a job description.")

        prompt = self._build_prompt(job, description)
        try:
            tailored_text = self._request_completion(prompt)
        except RuntimeError as primary_error:
            if not self.fallback_service:
                raise
            logging.warning(
                "%s resume generation failed; trying local %s fallback: %s",
                self.provider,
                self.fallback_service.provider,
                primary_error,
            )
            try:
                tailored_text = self.fallback_service._request_completion(
                    prompt
                )
            except RuntimeError as fallback_error:
                raise RuntimeError(
                    f"Both {self.provider} and "
                    f"{self.fallback_service.provider} resume generation "
                    "failed. "
                    f"Primary error: {primary_error}; "
                    f"fallback error: {fallback_error}"
                ) from fallback_error
        if not tailored_text.strip():
            raise RuntimeError("The configured AI provider returned an empty resume draft.")

        output_path = self._output_path(job)
        self._write_docx(output_path, job, tailored_text.strip())
        return output_path

    def _build_prompt(self, job: dict, description: str) -> str:
        return (
            "Create a concise, ATS-readable resume draft for this job using only "
            "facts explicitly present in the source resume. Reorder and rephrase "
            "existing information to emphasize relevant experience and skills, "
            "but do not invent employers, dates, degrees, skills, certifications, "
            "achievements, metrics, or responsibilities. Do not claim a skill "
            "from the job description unless the source resume supports it. "
            "If relevant information is missing, omit it rather than guessing. "
            "Return only the resume text, with clear section headings and "
            "plain-text bullet points.\n\n"
            f"Target job: {job.get('title', 'Unknown')}\n"
            f"Company: {job.get('company', 'Unknown')}\n"
            f"Location: {job.get('location', 'Unknown')}\n\n"
            "Source resume:\n"
            f"{self.resume_text}\n\n"
            "Job description:\n"
            f"{description}"
        )

    def _request_completion(self, prompt: str) -> str:
        if self.provider == "ollama":
            url = f"{self.base_url}/api/chat"
            headers = {"content-type": "application/json"}
            payload = {
                "model": self.model,
                "stream": False,
                "options": {"temperature": 0.2},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You edit resumes faithfully. Never add or infer "
                            "candidate facts that are not in the source resume."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
        elif self.provider == "anthropic":
            url = self.ANTHROPIC_API_URL
            headers = {
                "anthropic-version": self.API_VERSION,
                "x-api-key": self.api_key or "",
                "content-type": "application/json",
            }
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "system": (
                    "You edit resumes faithfully. Never add or infer candidate "
                    "facts that are not in the source resume."
                ),
                "messages": [{"role": "user", "content": prompt}],
            }
        else:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent"
            )
            headers = {
                "x-goog-api-key": self.api_key or "",
                "content-type": "application/json",
            }
            payload = {
                "system_instruction": {
                    "parts": [
                        {
                            "text": (
                                "You edit resumes faithfully. Never add or "
                                "infer candidate facts that are not in the "
                                "source resume."
                            )
                        }
                    ]
                },
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                "generationConfig": {"temperature": 0.2},
            }

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            for attempt in range(3):
                try:
                    with urlopen(request, timeout=180) as response:
                        result = json.loads(response.read().decode("utf-8"))
                    break
                except TimeoutError as error:
                    if attempt < 2:
                        time.sleep(2**attempt)
                        continue
                    raise RuntimeError(
                        f"{self.provider} request timed out after three "
                        "attempts. Check your connection and try again."
                    ) from error
                except HTTPError as error:
                    if error.code in {500, 502, 503, 504} and attempt < 2:
                        time.sleep(2**attempt)
                        continue
                    raise RuntimeError(
                        f"{self.provider} request failed with HTTP "
                        f"{error.code}. Check the provider, model availability, "
                        "API key, and quota."
                    ) from error
                except URLError as error:
                    if isinstance(error.reason, TimeoutError) and attempt < 2:
                        time.sleep(2**attempt)
                        continue
                    raise
        except URLError as error:
            raise RuntimeError(
                f"Could not reach {self.provider}: {error.reason}. "
                "Check your network connection and provider configuration."
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"{self.provider} returned an invalid response."
            ) from error

        if self.provider == "ollama":
            message = result.get("message")
            text = (
                message.get("content", "")
                if isinstance(message, dict)
                else ""
            )
        elif self.provider == "gemini":
            candidates = result.get("candidates")
            if not isinstance(candidates, list):
                raise RuntimeError("Gemini response did not contain candidates.")
            parts = (
                candidates[0].get("content", {}).get("parts", [])
                if candidates and isinstance(candidates[0], dict)
                else []
            )
            text = "\n".join(
                part["text"]
                for part in parts
                if isinstance(part, dict)
                and isinstance(part.get("text"), str)
            )
        else:
            content = result.get("content")
            if not isinstance(content, list):
                raise RuntimeError(
                    "Anthropic response did not contain content."
                )
            text = "\n".join(
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )
        if not text:
            raise RuntimeError(
                f"{self.provider} response did not contain resume text."
            )
        return text

    def _output_path(self, job: dict) -> Path:
        label = " ".join(
            str(job.get(key) or "")
            for key in ("title", "company")
        ).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:70]
        job_hash = hashlib.sha256(
            str(job.get("job_url") or label).encode("utf-8")
        ).hexdigest()[:10]
        filename = f"{slug or 'job'}-{job_hash}.docx"
        return self.output_directory / filename

    @staticmethod
    def _write_docx(path: Path, job: dict, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = Document()
        document.add_paragraph(
            "AI-assisted draft. Review all facts and wording before using."
        )
        document.add_heading(
            f"{job.get('title', 'Tailored Resume')} - "
            f"{job.get('company', 'Company')}",
            level=0,
        )

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    document.add_heading(heading, level=1)
            elif stripped.startswith(("- ", "* ", "• ")):
                document.add_paragraph(stripped[2:].strip(), style="List Bullet")
            else:
                document.add_paragraph(stripped)
        document.save(path)
