import json
import re
import unicodedata
from datetime import date
from pathlib import Path


class ProfileTextProposal:
    """Generate daily, reviewable headline and About text from a resume."""

    MAX_HEADLINE_ATTEMPTS = 3

    def __init__(self, ai_service, history_path: str | Path):
        self.ai_service = ai_service
        self.history_path = Path(history_path)

    def generate(
        self,
        platform: str,
        prompts: dict,
        output_directory: str | Path,
        today: date | None = None,
    ) -> Path:
        generation_date = today or date.today()
        history = self._load_history()
        platform_history = history.setdefault(platform, [])
        day = generation_date.isoformat()
        output_path = Path(output_directory) / f"{platform}_{day}.json"

        if output_path.is_file():
            return output_path

        previous_headlines = [
            item["headline"]
            for item in platform_history
            if isinstance(item, dict)
            and isinstance(item.get("headline"), str)
        ]
        result = self._create_text(prompts, previous_headlines)
        proposal = {
            "platform": platform,
            "created_on": day,
            "source_resume": str(self.ai_service.resume_path),
            "headline": result["headline"],
            "about": result["about"],
            "review_required": True,
            "applied": False,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.save(proposal, output_path)
        platform_history.append(
            {"date": day, "headline": result["headline"]}
        )
        self._write_json(self.history_path, history)
        return output_path

    @staticmethod
    def save(proposal: dict, path: str | Path) -> Path:
        proposal_path = Path(path)
        ProfileTextProposal._write_json(proposal_path, proposal)
        return proposal_path

    def _create_text(
        self,
        prompts: dict,
        previous_headlines: list[str],
    ) -> dict[str, str]:
        headline_prompt = self._prompt_value(prompts, "headline_prompt")
        about_prompt = self._prompt_value(prompts, "about_prompt")
        normalized_previous = {
            self._normalize_headline(headline)
            for headline in previous_headlines
        }
        previous_text = (
            json.dumps(previous_headlines, ensure_ascii=True)
            if previous_headlines
            else "[]"
        )

        for attempt in range(self.MAX_HEADLINE_ATTEMPTS):
            retry_instruction = (
                "The previous proposed headline repeated an earlier one. "
                "Choose a meaningfully different wording."
                if attempt
                else ""
            )
            prompt = (
                "Create a professional profile headline and About section "
                "using only facts explicitly supported by the source resume. "
                "Do not invent skills, job titles, experience, achievements, "
                "metrics, education, or certifications. Return valid JSON "
                'only with exactly these string keys: "headline" and "about". '
                "Keep both concise and truthful. The headline must be "
                "different from every previously used headline, including "
                "differences in capitalization or punctuation only. "
                f"Previously used headlines: {previous_text}\n"
                f"Platform headline instructions: {headline_prompt}\n"
                f"Platform About instructions: {about_prompt}\n"
                f"{retry_instruction}\n\n"
                f"Source resume:\n{self.ai_service.resume_text}"
            )
            result = self._parse_response(
                self.ai_service.complete_prompt(
                    prompt,
                    response_format="json",
                )
            )
            if self._normalize_headline(result["headline"]) not in (
                normalized_previous
            ):
                return result

        raise RuntimeError(
            "The AI repeated a previously used headline after "
            f"{self.MAX_HEADLINE_ATTEMPTS} attempts. No proposal was saved."
        )

    @staticmethod
    def _prompt_value(prompts: dict, key: str) -> str:
        value = prompts.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Configure a non-empty '{key}' for this platform."
            )
        return value.strip()

    @staticmethod
    def _parse_response(response: str) -> dict[str, str]:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise ValueError(
                "The AI returned invalid JSON for the profile text proposal."
            ) from error
        if (
            not isinstance(data, dict)
            or set(data) != {"headline", "about"}
            or any(
                not isinstance(data[field], str) or not data[field].strip()
                for field in ("headline", "about")
            )
        ):
            raise ValueError(
                "The profile text proposal must contain non-empty "
                "'headline' and 'about' strings only."
            )
        return {
            "headline": data["headline"].strip(),
            "about": data["about"].strip(),
        }

    @staticmethod
    def _normalize_headline(headline: str) -> str:
        normalized = unicodedata.normalize("NFKC", headline).casefold()
        return " ".join(re.findall(r"\w+", normalized))

    def _load_history(self) -> dict:
        if not self.history_path.exists():
            return {}
        try:
            history = json.loads(
                self.history_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Could not read profile text history: "
                f"{self.history_path}"
            ) from error
        if not isinstance(history, dict) or any(
            not isinstance(items, list) for items in history.values()
        ):
            raise RuntimeError(
                "Profile text history has an invalid format: "
                f"{self.history_path}"
            )
        return history

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
