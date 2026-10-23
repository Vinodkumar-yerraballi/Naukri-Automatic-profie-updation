import hashlib
import json
from datetime import datetime
from pathlib import Path

from src.ingestion.naukri_browser import NaukriBrowser


class NaukriResumeUploader:
    """Upload a changed source resume and remember successful uploads."""

    def __init__(
        self,
        state_path: str | Path = "data/profile_resume_upload.json",
    ):
        self.state_path = Path(state_path)

    def update_if_changed(
        self,
        browser: NaukriBrowser,
        resume_path: str | Path,
    ) -> bool:
        resume = Path(resume_path)
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        digest = self._file_hash(resume)
        previous_digest = self._previous_hash()
        if digest == previous_digest:
            print(
                "Naukri profile resume is already up to date; "
                "the source file has not changed."
            )
            return False

        browser.update_profile_resume(resume)
        self._save_hash(digest, resume)
        return True

    @staticmethod
    def _file_hash(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as resume_file:
            for chunk in iter(lambda: resume_file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _previous_hash(self) -> str | None:
        if not self.state_path.is_file():
            return None
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Could not read resume-upload state: {self.state_path}"
            ) from error
        digest = state.get("sha256")
        return digest if isinstance(digest, str) else None

    def _save_hash(self, digest: str, resume_path: Path) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "sha256": digest,
            "file_name": resume_path.name,
            "uploaded_at": datetime.now().astimezone().isoformat(),
        }
        temporary_path = self.state_path.with_suffix(
            self.state_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.state_path)
