import json
import re
from datetime import datetime
from pathlib import Path

from src.profile.resume_tailoring import ResumeTailoringService


PROFILE_SECTIONS = (
    "headline",
    "summary",
    "skills",
    "employment",
    "education",
    "projects",
    "certifications",
)


class ResumeProfileProposal:
    """Create a reviewable profile update from resume-supported facts."""

    def __init__(self, ai_service: ResumeTailoringService):
        self.ai_service = ai_service

    def create(self, sections: list[str]) -> dict:
        requested = set(sections)
        unknown = requested.difference(PROFILE_SECTIONS)
        if unknown:
            raise ValueError(
                f"Unsupported profile sections: {', '.join(sorted(unknown))}"
            )
        if not requested:
            raise ValueError("Select at least one profile section.")

        prompt = self._build_prompt(requested)
        raw_response = self.ai_service._request_completion(prompt)
        data = self._parse_response(raw_response)
        return {
            "created_at": datetime.now().astimezone().isoformat(),
            "source_resume": str(self.ai_service.resume_path),
            "sections": sorted(requested),
            "data": data,
            "review_required": True,
            "unmatched_existing_records": "preserve",
        }

    def save(self, proposal: dict, path: str | Path) -> Path:
        proposal_path = Path(path)
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = proposal_path.with_suffix(
            proposal_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(proposal, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(proposal_path)
        return proposal_path

    def _build_prompt(self, sections: set[str]) -> str:
        schema = {
            "headline": "string or null",
            "summary": "string or null",
            "skills": ["strings explicitly supported by the resume"],
            "employment": [
                {
                    "title": "string or null",
                    "company": "string or null",
                    "location": "string or null",
                    "start_date": "string or null",
                    "end_date": "string or null",
                    "is_current": "boolean or null",
                    "description": "string or null",
                }
            ],
            "education": [
                {
                    "qualification": "string or null",
                    "specialization": "string or null",
                    "institution": "string or null",
                    "start_year": "string or null",
                    "end_year": "string or null",
                }
            ],
            "projects": [
                {
                    "title": "string or null",
                    "description": "string or null",
                    "skills": ["strings explicitly supported by the resume"],
                }
            ],
            "certifications": [
                {
                    "name": "string or null",
                    "issuer": "string or null",
                    "year": "string or null",
                }
            ],
        }
        return (
            "Extract a proposed Naukri profile update from the source resume. "
            "Return valid JSON only, with exactly these top-level keys and "
            "matching value shapes:\n"
            f"{json.dumps(schema, ensure_ascii=True)}\n"
            f"Prepare only these sections: {json.dumps(sorted(sections))}.\n"
            "Rules: include only facts explicitly stated in the resume; do "
            "not invent or infer employers, titles, dates, skills, degrees, "
            "certifications, metrics, or responsibilities. Use null or an "
            "empty list when the resume does not support a field. Do not "
            "include phone numbers, email addresses, date of birth, salary, "
            "notice period, or other personal/contact details. Do not remove "
            "or replace any existing profile records not found in the resume. "
            "Keep headline and summary concise and factual. Return no Markdown "
            "fences or commentary.\n\n"
            "Source resume:\n"
            f"{self.ai_service.resume_text}"
        )

    @staticmethod
    def _parse_response(response: str) -> dict:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise ValueError(
                "The AI returned invalid JSON for the profile proposal."
            ) from error

        if not isinstance(data, dict):
            raise ValueError("The profile proposal must be a JSON object.")

        expected_keys = set(PROFILE_SECTIONS)
        if set(data) != expected_keys:
            raise ValueError(
                "The AI profile proposal has an unexpected field set."
            )

        for key in ("headline", "summary"):
            if data[key] is not None and not isinstance(data[key], str):
                raise ValueError(f"Profile field '{key}' must be text or null.")
        for key in ("skills", "employment", "education", "projects", "certifications"):
            if not isinstance(data[key], list):
                raise ValueError(f"Profile field '{key}' must be a list.")
        for skill in data["skills"]:
            if not isinstance(skill, str):
                raise ValueError("Each proposed skill must be text.")
        for key in ("employment", "education", "projects", "certifications"):
            if any(not isinstance(item, dict) for item in data[key]):
                raise ValueError(f"Each '{key}' entry must be an object.")

        return data
