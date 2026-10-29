import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import (
    Error as PlaywrightError,
    Locator,
    Playwright,
    sync_playwright,
)


PLATFORM_PAGES = {
    "foundit": {
        "login": (
            "https://www.foundit.in/rio/login?"
            "return_url=%2Fseeker%2Fprofile"
        ),
        "profile": "https://www.foundit.in/seeker/profile",
    },
    "indeed": {
        "login": "https://secure.indeed.com/",
        "profile": "https://profile.indeed.com/",
    },
}

RESUME_FILE_INPUT_SELECTOR = (
    "input[type='file'][accept*='.pdf' i], "
    "input[type='file'][accept*='.doc' i], "
    "input[type='file'][name*='resume' i], "
    "input[type='file'][id*='resume' i], "
    "input[type='file'][aria-label*='resume' i]"
)


class CandidatePlatformBrowser:
    """Browser session for user-signed-in Foundit and Indeed profiles."""

    def __init__(self, platform: str, headless: bool = False):
        if platform not in PLATFORM_PAGES:
            raise ValueError(f"Unsupported resume platform: {platform}")
        self.platform = platform
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None
        self._owns_playwright = False

    def start_persistent(
        self,
        user_data_dir: str | Path,
        playwright: Playwright | None = None,
    ) -> None:
        profile_dir = Path(user_data_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        if playwright is None:
            self.playwright = sync_playwright().start()
            self._owns_playwright = True
        else:
            self.playwright = playwright
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir.resolve()),
            headless=self.headless,
            viewport={"width": 1440, "height": 900},
        )
        self.page = self.context.new_page()

    def setup_login(self) -> None:
        if self.page is None:
            raise RuntimeError("Browser is not started.")
        self.page.goto(
            PLATFORM_PAGES[self.platform]["login"],
            wait_until="domcontentloaded",
            timeout=60000,
        )

    def update_profile_resume(self, resume_path: str | Path) -> None:
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        resume = Path(resume_path).resolve()
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        self.page.goto(
            PLATFORM_PAGES[self.platform]["profile"],
            wait_until="domcontentloaded",
            timeout=60000,
        )
        self.page.wait_for_timeout(2000)

        current_url = self.page.url.lower()
        body = self.page.locator("body").inner_text().lower()
        if any(marker in current_url for marker in ("login", "/auth")):
            raise RuntimeError(
                f"{self.platform.title()} is not signed in. Run "
                f"`python main.py --setup-{self.platform}-session` first."
            )
        if any(
            marker in body
            for marker in (
                "verify you are human",
                "security check",
                "captcha",
                "unusual traffic",
            )
        ):
            raise RuntimeError(
                f"{self.platform.title()} requested a security check. "
                "Complete it manually and retry."
            )

        upload_control = self._resume_upload_control()
        if upload_control.count() == 0:
            upload_action = self.page.get_by_text(
                re.compile(
                    r"(upload|update|add)\s+(your\s+)?resume",
                    re.IGNORECASE,
                )
            )
            if upload_action.count() > 0:
                upload_action.first.click(timeout=10000)
                self.page.wait_for_timeout(1000)
            upload_control = self._resume_upload_control()

        if upload_control.count() == 0:
            raise RuntimeError(
                f"Could not find a resume upload control on the "
                f"{self.platform.title()} profile page; no file was uploaded."
            )

        upload_control.first.set_input_files(str(resume))
        self.page.wait_for_timeout(1500)

        save_control = self.page.locator(
            "button:has-text('Upload'), button:has-text('Save'), "
            "button:has-text('Update'), "
            "input[type='submit'][value*='upload' i], "
            "input[type='submit'][value*='save' i], "
            "input[type='button'][value*='upload' i], "
            "input[type='button'][value*='save' i]"
        )
        if save_control.count() > 0 and save_control.first.is_visible():
            save_control.first.click(timeout=10000)
            self.page.wait_for_timeout(4000)

        confirmation_text = self.page.locator("body").inner_text().lower()
        success_phrases = (
            "resume uploaded",
            "resume updated",
            "successfully uploaded",
            "successfully updated",
            "resume saved",
        )
        if not any(phrase in confirmation_text for phrase in success_phrases):
            raise RuntimeError(
                f"{self.platform.title()} did not confirm the resume upload. "
                "Check the profile manually before retrying."
            )

    def update_profile_fields(self, proposal: dict) -> list[str]:
        if self.platform != "foundit":
            raise RuntimeError(
                f"Automatic profile-field updates are not implemented for "
                f"{self.platform.title()}."
            )
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        data = proposal.get("data")
        if not isinstance(data, dict):
            raise ValueError("The profile proposal has no valid data object.")

        self.page.goto(
            PLATFORM_PAGES[self.platform]["profile"],
            wait_until="domcontentloaded",
            timeout=60000,
        )
        self.page.wait_for_timeout(2000)
        if "login" in self.page.url.lower():
            raise RuntimeError(
                "Foundit is not signed in. Run "
                "`python main.py --setup-foundit-session` first."
            )
        if self.page.title().lower() == "access denied":
            raise RuntimeError(
                "Foundit denied access to the profile page. No profile "
                "fields were changed."
            )

        changed = []
        failures = []
        for section, updater, value in (
            ("skills", self._update_foundit_skills, data.get("skills", [])),
            (
                "employment",
                self._update_foundit_experience,
                data.get("employment", []),
            ),
            (
                "projects",
                self._update_foundit_projects,
                data.get("projects", []),
            ),
        ):
            try:
                if updater(value):
                    changed.append(section)
            except (PlaywrightError, RuntimeError, ValueError) as error:
                failures.append(
                    f"{section}: {type(error).__name__}: {error}"
                )
        if failures:
            raise RuntimeError(
                "Some Foundit profile fields could not be updated: "
                + "; ".join(failures)
            )
        return changed

    def _update_foundit_skills(self, skills: object) -> bool:
        if not isinstance(skills, list):
            raise ValueError("Proposed skills must be a list.")
        values = list(
            dict.fromkeys(
                skill.strip()
                for skill in skills
                if isinstance(skill, str) and skill.strip()
            )
        )
        if not values:
            return False

        modal = self._open_foundit_modal("Skills")
        try:
            field = modal.locator("#skills")
            if field.count() != 1:
                raise RuntimeError(
                    "Foundit's skills editor changed; no skills were saved."
                )
            existing = {
                text.strip().casefold()
                for text in modal.locator("button").all_inner_texts()
                if text.strip()
                and text.strip().casefold() not in {"save", "close"}
            }
            missing = [
                skill
                for skill in values
                if skill.casefold() not in existing
            ]
            if not missing:
                self._close_foundit_modal(modal)
                return False

            for skill in missing:
                field.fill(skill)
                self.page.wait_for_timeout(500)
                options = self.page.locator("li, [role='option']")
                exact_match = None
                for option in options.all():
                    if (
                        option.is_visible()
                        and option.inner_text().strip().casefold()
                        == skill.casefold()
                    ):
                        exact_match = option
                        break
                if exact_match is None:
                    raise RuntimeError(
                        f"Foundit did not offer an exact skill match for "
                        f"'{skill}'. No additional skills were saved."
                    )
                exact_match.click(timeout=10000)
                self.page.wait_for_timeout(250)

            self._save_foundit_modal(modal)
            return True
        except (PlaywrightError, RuntimeError, ValueError):
            self._close_foundit_modal_if_open()
            raise

    def _update_foundit_experience(self, employment: object) -> bool:
        if not isinstance(employment, list):
            raise ValueError("Proposed employment must be a list.")
        entries = [
            item
            for item in employment
            if isinstance(item, dict)
            and isinstance(item.get("title"), str)
            and item["title"].strip()
            and isinstance(item.get("company"), str)
            and item["company"].strip()
            and isinstance(item.get("is_current"), bool)
        ]
        if not entries:
            return False

        existing = self._foundit_existing_records(
            "Edit work experience",
            ("jobTitle", "manualCurrentJobTitle"),
            ("company", "manualCompany"),
        )
        changed = False
        for entry in entries:
            title = entry["title"].strip()
            company = entry["company"].strip()
            identity = (title.casefold(), company.casefold())
            if identity in existing:
                continue

            modal = self._open_foundit_modal("Add work experience")
            try:
                self._fill_foundit_experience(modal, entry)
                self._save_foundit_modal(modal)
            except (PlaywrightError, RuntimeError, ValueError):
                self._close_foundit_modal_if_open()
                raise
            existing.add(identity)
            changed = True
        return changed

    def _fill_foundit_experience(self, modal: Locator, entry: dict) -> None:
        title = entry["title"].strip()
        title_field = modal.locator("#jobTitle")
        company_field = modal.locator("#company")
        description_field = modal.locator("#title")
        if any(
            field.count() != 1
            for field in (title_field, company_field, description_field)
        ):
            raise RuntimeError(
                "Foundit's experience editor changed; no experience was saved."
            )

        title_field.fill(title)
        self.page.wait_for_timeout(500)
        title_option = None
        for option in self.page.locator("li, [role='option']").all():
            if (
                option.is_visible()
                and option.inner_text().strip().casefold()
                == title.casefold()
            ):
                title_option = option
                break
        if title_option is None:
            raise RuntimeError(
                f"Foundit did not offer an exact job-title match for "
                f"'{title}'. No experience was saved."
            )
        title_option.click(timeout=10000)
        company_field.fill(entry["company"].strip())
        description = entry.get("description")
        if isinstance(description, str) and description.strip():
            description_field.fill(description.strip())

        start_year, start_month = self._date_parts(entry.get("start_date"))
        if start_year:
            self._select_foundit_dropdown_value(
                modal,
                "startYear",
                start_year,
            )
        if start_month:
            self._select_foundit_dropdown_value(
                modal,
                "startMonth",
                start_month,
            )

        current_checkbox = modal.locator("#checkbox")
        if current_checkbox.count() != 1:
            raise RuntimeError(
                "Foundit's current-employment control changed; no "
                "experience was saved."
            )
        if entry["is_current"]:
            current_checkbox.check()
        else:
            current_checkbox.uncheck()
            self.page.wait_for_timeout(250)
            end_year, end_month = self._date_parts(entry.get("end_date"))
            if end_year and modal.locator("#endYear").count() == 1:
                self._select_foundit_dropdown_value(
                    modal,
                    "endYear",
                    end_year,
                )
            if end_month and modal.locator("#endMonth").count() == 1:
                self._select_foundit_dropdown_value(
                    modal,
                    "endMonth",
                    end_month,
                )

    def _update_foundit_projects(self, projects: object) -> bool:
        if not isinstance(projects, list):
            raise ValueError("Proposed projects must be a list.")
        entries = [
            item
            for item in projects
            if isinstance(item, dict)
            and isinstance(item.get("title"), str)
            and item["title"].strip()
        ]
        if not entries:
            return False

        existing = self._foundit_existing_records(
            "Edit project",
            ("title",),
        )
        changed = False
        for entry in entries:
            title = entry["title"].strip()
            if (title.casefold(),) in existing:
                continue

            modal = self._open_foundit_modal("Add project")
            try:
                modal.locator("#title").fill(title)
                description = entry.get("description")
                if isinstance(description, str) and description.strip():
                    modal.locator("#description").fill(description.strip())
                self._save_foundit_modal(modal)
            except (PlaywrightError, RuntimeError, ValueError):
                self._close_foundit_modal_if_open()
                raise
            existing.add((title.casefold(),))
            changed = True
        return changed

    def _foundit_existing_records(
        self,
        heading: str,
        primary_fields: tuple[str, ...],
        secondary_fields: tuple[str, ...] = (),
    ) -> set[tuple[str, ...]]:
        records = set()
        edit_buttons = self.page.locator("#SECTION_EDIT_BUTTON")
        for index in range(edit_buttons.count()):
            edit_buttons.nth(index).click(timeout=10000)
            modal = self._foundit_modal()
            modal_heading = self._foundit_modal_heading(modal)
            if modal_heading.casefold() == heading.casefold():
                primary = self._first_filled_value(modal, primary_fields)
                secondary = self._first_filled_value(modal, secondary_fields)
                if primary and (secondary or not secondary_fields):
                    record = (primary.casefold(),)
                    if secondary:
                        record += (secondary.casefold(),)
                    records.add(record)
            self._close_foundit_modal(modal)
        return records

    def _select_foundit_dropdown_value(
        self,
        modal: Locator,
        field_id: str,
        value: str,
    ) -> None:
        field = modal.locator(f"#{field_id}")
        if field.count() != 1:
            raise RuntimeError(
                f"Foundit's {field_id} selector changed; no experience "
                "was saved."
            )
        field.click(timeout=10000)
        self.page.wait_for_timeout(200)
        for option in self.page.locator("li, [role='option']").all():
            if (
                option.is_visible()
                and option.inner_text().strip().casefold()
                == value.casefold()
            ):
                option.click(timeout=10000)
                return
        raise RuntimeError(
            f"Foundit did not offer the requested value for {field_id}; "
            "no experience was saved."
        )

    def _open_foundit_modal(self, heading: str) -> Locator:
        edit_buttons = self.page.locator("#SECTION_EDIT_BUTTON")
        for index in range(edit_buttons.count()):
            edit_buttons.nth(index).click(timeout=10000)
            modal = self._foundit_modal()
            if self._foundit_modal_heading(modal).casefold() == heading.casefold():
                return modal
            self._close_foundit_modal(modal)
        raise RuntimeError(
            f"Could not find Foundit's '{heading}' profile editor; no "
            "profile changes were made."
        )

    def _foundit_modal(self) -> Locator:
        modal = self.page.locator('[data-portal="global-ui-modal"]').last
        headings = modal.locator("h1, h2, h3, h4, [role='heading']")
        headings.first.wait_for(state="visible", timeout=10000)
        return modal

    @staticmethod
    def _foundit_modal_heading(modal: Locator) -> str:
        headings = modal.locator("h1, h2, h3, h4, [role='heading']")
        return headings.first.inner_text().strip() if headings.count() else ""

    @staticmethod
    def _first_filled_value(modal: Locator, field_ids: tuple[str, ...]) -> str:
        for field_id in field_ids:
            field = modal.locator(f"#{field_id}")
            if field.count() == 1:
                value = field.first.input_value().strip()
                if value:
                    return value
        return ""

    def _save_foundit_modal(self, modal: Locator) -> None:
        save_button = modal.get_by_role("button", name="Save", exact=True)
        if save_button.count() != 1:
            raise RuntimeError(
                "Foundit's profile editor has no unique Save button; "
                "the proposed fields were not saved."
            )
        save_button.click(timeout=10000)
        self.page.wait_for_timeout(1000)
        close_button = modal.locator('[aria-label="Close"]')
        if close_button.count() and close_button.first.is_visible():
            raise RuntimeError(
                "Foundit kept the profile editor open after Save. Check "
                "validation messages and the profile manually."
            )

    def _close_foundit_modal(self, modal: Locator) -> None:
        close_button = modal.locator('[aria-label="Close"]')
        if close_button.count() == 1 and close_button.is_visible():
            close_button.click(timeout=5000)
            close_button.wait_for(state="hidden", timeout=5000)
            self.page.wait_for_timeout(400)

    def _close_foundit_modal_if_open(self) -> None:
        modal = self.page.locator('[data-portal="global-ui-modal"]').last
        close_button = modal.locator('[aria-label="Close"]')
        if close_button.count() and close_button.is_visible():
            self._close_foundit_modal(modal)

    @staticmethod
    def _date_parts(value: object) -> tuple[str | None, str | None]:
        if not isinstance(value, str):
            return None, None
        year_match = re.search(r"\b(?:19|20)\d{2}\b", value)
        if not year_match:
            return None, None
        month_match = re.search(
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
            r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
            r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
            value,
            re.IGNORECASE,
        )
        month = month_match.group(1).title() if month_match else None
        return year_match.group(), month

    def _resume_upload_control(self) -> Locator:
        matching_controls = self.page.locator(RESUME_FILE_INPUT_SELECTOR)
        if matching_controls.count() == 1:
            return matching_controls.first
        if matching_controls.count() > 1:
            raise RuntimeError(
                f"Multiple resume upload controls were found on the "
                f"{self.platform.title()} profile page; no file was uploaded."
            )

        file_controls = self.page.locator("input[type='file']")
        if file_controls.count() > 1:
            raise RuntimeError(
                f"Multiple file upload controls were found on the "
                f"{self.platform.title()} profile page and none was clearly "
                "identified as the resume field; no file was uploaded."
            )
        return file_controls.first

    def close(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None
        if self.playwright is not None and self._owns_playwright:
            self.playwright.stop()
        self.playwright = None
        self._owns_playwright = False


class PlatformResumeUploader:
    """Upload a changed resume to one platform and track confirmed uploads."""

    def __init__(self, platform: str, state_path: str | Path):
        if platform not in PLATFORM_PAGES:
            raise ValueError(f"Unsupported resume platform: {platform}")
        self.platform = platform
        self.state_path = Path(state_path)

    def update_if_changed(
        self,
        browser: CandidatePlatformBrowser,
        resume_path: str | Path,
    ) -> bool:
        resume = Path(resume_path)
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        digest = self._file_hash(resume)
        previous_digest = self._previous_hash()
        if digest == previous_digest:
            print(
                f"{self.platform.title()} profile resume is already up to "
                "date; the source file has not changed."
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
                f"Could not read {self.platform} resume-upload state: "
                f"{self.state_path}"
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


class PlatformProfileUpdater:
    """Apply resume-supported profile fields once per source-resume version."""

    def __init__(self, platform: str, state_path: str | Path):
        if platform not in PLATFORM_PAGES:
            raise ValueError(f"Unsupported profile platform: {platform}")
        self.platform = platform
        self.state_path = Path(state_path)

    def is_current(self, resume_path: str | Path) -> bool:
        resume = Path(resume_path)
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")
        return self._previous_hash() == self._file_hash(resume)

    def update_if_changed(
        self,
        browser: CandidatePlatformBrowser,
        resume_path: str | Path,
        proposal: dict,
    ) -> list[str]:
        resume = Path(resume_path)
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        digest = self._file_hash(resume)
        if digest == self._previous_hash():
            return []

        changed = browser.update_profile_fields(proposal)
        self._save_hash(digest, resume)
        return changed

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
                f"Could not read {self.platform} profile-update state: "
                f"{self.state_path}"
            ) from error
        digest = state.get("sha256")
        return digest if isinstance(digest, str) else None

    def _save_hash(self, digest: str, resume_path: Path) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "sha256": digest,
            "file_name": resume_path.name,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        temporary_path = self.state_path.with_suffix(
            self.state_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.state_path)
