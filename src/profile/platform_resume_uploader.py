import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

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
    "shine": {
        "login": "https://www.shine.com/pages/myshine/login",
        "profile": "https://www.shine.com/myshine/resume/upload",
        "profile_edit": "https://www.shine.com/myshine/myprofile",
    },
    "hirist": {
        "login": "https://www.hirist.tech/login",
        "profile": "https://www.hirist.tech/candidate/profile",
    },
    "wellfound": {
        "login": "https://wellfound.com/login",
        "profile": "https://wellfound.com/users/edit",
    },
}
PROFILE_STATE_PLATFORMS = {"foundit", "naukri", "shine"}


class ProfileFieldBrowser(Protocol):
    def update_profile_fields(self, proposal: dict) -> list[str]: ...


RESUME_FILE_INPUT_SELECTOR = (
    "input[type='file'][accept*='.pdf' i], "
    "input[type='file'][accept*='.doc' i], "
    "input[type='file'][name*='resume' i], "
    "input[type='file'][id*='resume' i], "
    "input[type='file'][aria-label*='resume' i]"
)


class CandidatePlatformBrowser:
    """Browser session for user-signed-in candidate profiles."""

    def __init__(
        self,
        platform: str,
        headless: bool = False,
        platform_config: dict | None = None,
    ):
        if platform not in PLATFORM_PAGES:
            raise ValueError(f"Unsupported resume platform: {platform}")
        self.platform = platform
        self.headless = headless
        self.pages = dict(PLATFORM_PAGES[platform])
        self.session_state_path = None
        if platform_config:
            for page_name in ("login", "profile", "profile_edit"):
                configured_url = platform_config.get(f"{page_name}_url")
                if isinstance(configured_url, str) and configured_url.strip():
                    self.pages[page_name] = configured_url.strip()
            if platform == "shine":
                self.session_state_path = Path(
                    platform_config.get(
                        "session_state_file",
                        "data/shine_session_state.json",
                    )
                )
        elif platform == "shine":
            self.session_state_path = Path("data/shine_session_state.json")
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
        pages = self.context.pages
        self.page = pages[0] if pages else self.context.new_page()
        if self.platform == "shine":
            self._restore_shine_session()

    def setup_login(self) -> None:
        if self.page is None:
            raise RuntimeError("Browser is not started.")
        self.page.goto(
            self.pages["login"],
            wait_until="domcontentloaded",
            timeout=60000,
        )

    def verify_shine_session(self) -> None:
        if self.platform != "shine":
            raise ValueError("Session verification is only implemented for Shine.")
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        response = self.page.goto(
            self.pages["profile"],
            wait_until="domcontentloaded",
            timeout=60000,
        )
        response_status = (
            getattr(response, "status", None) if response is not None else None
        )
        current_url = self.page.url.lower()
        if (
            (response_status is not None and response_status >= 400)
            or "/myshine/login" in current_url
            or self.page.locator("#myfile").count() != 1
        ):
            raise RuntimeError(
                "Shine sign-in was not verified. In the opened browser, "
                "complete login until the resume-upload page appears, then "
                "run `python main.py --setup-shine-session` again."
            )
        self._save_shine_session()

    def prepare_profile_update(self) -> None:
        if self.platform != "shine":
            raise ValueError(
                "Profile editor preparation is only implemented for Shine."
            )
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        response = self.page.goto(
            self.pages["profile_edit"],
            wait_until="domcontentloaded",
            timeout=60000,
        )
        response_status = (
            getattr(response, "status", None) if response is not None else None
        )
        current_url = self.page.url.lower()
        profile_update_button = self.page.get_by_role(
            "button",
            name="Update",
            exact=True,
        )
        if (
            (response_status is not None and response_status >= 400)
            or "/myshine/login" in current_url
        ):
            raise RuntimeError(
                "Shine redirected to sign-in or returned an error while "
                "opening the profile editor. Complete sign-in in the "
                "browser, then run `python main.py --setup-shine-session` "
                "before retrying."
            )
        try:
            profile_update_button.wait_for(
                state="visible",
                timeout=30000,
            )
        except PlaywrightError as error:
            current_path = urlparse(self.page.url).path
            if "/myshine/login" in self.page.url.lower():
                raise RuntimeError(
                    "Shine redirected to sign-in while the profile editor "
                    "was loading. Run `python main.py "
                    "--setup-shine-session` and complete sign-in."
                ) from error
            raise RuntimeError(
                "Shine's profile editor did not finish loading: its Update "
                "button was not visible after 30 seconds "
                f"(current page: {current_path or 'unknown'})."
            ) from error

    def _restore_shine_session(self) -> None:
        if self.session_state_path is None or not self.session_state_path.is_file():
            return
        try:
            state = json.loads(
                self.session_state_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Could not read the saved Shine browser session state: "
                f"{self.session_state_path}"
            ) from error
        if not isinstance(state, dict):
            raise RuntimeError(
                "Saved Shine browser session state has an invalid format."
            )

        cookies = state.get("cookies", [])
        if not isinstance(cookies, list):
            raise RuntimeError(
                "Saved Shine browser session cookies have an invalid format."
            )
        if cookies:
            self.context.add_cookies(cookies)

        session_storage = state.get("session_storage", {})
        if not isinstance(session_storage, dict):
            raise RuntimeError(
                "Saved Shine session storage has an invalid format."
            )
        if session_storage:
            parsed_url = urlparse(self.pages["profile"])
            origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
            encoded_origin = json.dumps(origin)
            encoded_storage = json.dumps(session_storage)
            self.context.add_init_script(
                script=(
                    "(() => {"
                    f"if (window.location.origin === {encoded_origin}) {{"
                    f"const saved = {encoded_storage};"
                    "for (const [key, value] of Object.entries(saved)) {"
                    "window.sessionStorage.setItem(key, value);"
                    "}"
                    "}"
                    "})();"
                )
            )

    def _save_shine_session(self) -> None:
        if (
            self.session_state_path is None
            or self.context is None
            or self.page is None
        ):
            raise RuntimeError(
                "Cannot save Shine session state before the browser is ready."
            )

        session_storage = {}
        previous_session_storage = {}
        if self.session_state_path.is_file():
            try:
                previous_state = json.loads(
                    self.session_state_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError(
                    "Could not read the previous Shine browser session state: "
                    f"{self.session_state_path}"
                ) from error
            if isinstance(previous_state, dict):
                previous_storage = previous_state.get("session_storage", {})
                if isinstance(previous_storage, dict):
                    previous_session_storage = previous_storage

        storage_error = None
        for attempt in range(4):
            try:
                session_storage = self.page.evaluate(
                    """() => Object.fromEntries(
                        Array.from(
                            {length: sessionStorage.length},
                            (_, index) => {
                                const key = sessionStorage.key(index);
                                return [
                                    key,
                                    sessionStorage.getItem(key)
                                ];
                            }
                        )
                    )"""
                )
                if not isinstance(session_storage, dict):
                    raise RuntimeError(
                        "Shine returned invalid session storage data."
                    )
                storage_error = None
                break
            except PlaywrightError as error:
                if "execution context was destroyed" not in str(error).lower():
                    raise
                storage_error = error
                if attempt < 3:
                    self.page.wait_for_timeout(500 * (attempt + 1))

        if storage_error is not None:
            session_storage = previous_session_storage
            logging.warning(
                "Shine navigated while its session storage was being saved; "
                "preserving the previous storage state and saving current "
                "cookies. If later updates report that you are signed out, "
                "run --setup-shine-session again and wait for the page to "
                "finish loading before pressing Enter."
            )

        self.session_state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "cookies": self.context.cookies([self.pages["profile"]]),
            "session_storage": session_storage,
        }
        temporary_path = self.session_state_path.with_suffix(
            self.session_state_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.session_state_path)

    def update_profile_resume(self, resume_path: str | Path) -> None:
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        resume = Path(resume_path).resolve()
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        response = self.page.goto(
            self.pages["profile"],
            wait_until=(
                "commit" if self.platform == "hirist" else "domcontentloaded"
            ),
            timeout=60000,
        )
        self.page.wait_for_timeout(2000)

        current_url = self.page.url.lower()
        body = self.page.locator("body").inner_text().lower()
        response_status = (
            getattr(response, "status", None) if response is not None else None
        )
        page_title = self.page.title().strip()
        hirist_not_found = (
            self.platform == "hirist"
            and "looks like you" in body
            and "got lost" in body
        )
        if (
            (response_status is not None and response_status >= 400)
            or page_title.casefold() == "error page"
            or re.search(r"\b404\s+not\s+found\b", body)
            or hirist_not_found
        ):
            if hirist_not_found:
                status_detail = "Hirist displayed its missing-page message"
            elif response_status is not None:
                status_detail = (
                    f"HTTP {response_status}, page title {page_title!r}"
                )
            else:
                status_detail = f"page title {page_title!r}"
            raise RuntimeError(
                f"{self.platform.title()} profile page is unavailable "
                f"({status_detail}). Update "
                f"{self.platform}_profile.profile_url in "
                "config/job_preferences.yaml to the current resume/profile "
                "page URL."
            )
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
        if self.platform == "shine" and (
            "login with otp" in body
            or "login via otp" in body
            or "enter your email /phone number" in body
        ):
            raise RuntimeError(
                "Shine is displaying its sign-in form. Run "
                "`python main.py --setup-shine-session`, sign in, and retry."
            )

        if self.platform == "shine":
            self._upload_shine_resume(resume)
            return

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

    def _upload_shine_resume(self, resume: Path) -> None:
        if resume.stat().st_size > 5 * 1024 * 1024:
            raise ValueError(
                "Shine accepts resume files up to 5 MB. Reduce the file "
                "size and retry."
            )

        upload_control = self.page.locator("#myfile")
        if upload_control.count() != 1:
            raise RuntimeError(
                "Could not find Shine's resume upload control (#myfile) on "
                "the resume-upload page. No file was uploaded."
            )

        try:
            with self.page.expect_response(
                lambda response: (
                    "/api/v2/candidate/" in response.url
                    and "/resumefiles/" in response.url
                ),
                timeout=30000,
            ) as response_info:
                upload_control.set_input_files(str(resume))
            response = response_info.value
        except PlaywrightError as error:
            raise RuntimeError(
                "Shine did not return a response for the resume upload. "
                "Check the profile manually before retrying."
            ) from error

        if not 200 <= response.status < 300:
            raise RuntimeError(
                "Shine rejected the resume upload with HTTP "
                f"{response.status}. Check the file format and profile."
            )

        try:
            result = response.json()
        except PlaywrightError:
            result = None
        if isinstance(result, dict):
            if result.get("success") is False:
                detail = (
                    result.get("message")
                    or result.get("detail")
                    or "the site reported an unsuccessful upload"
                )
                raise RuntimeError(f"Shine resume upload failed: {detail}")
            errors = result.get("errors") or result.get("non_field_errors")
            if errors:
                raise RuntimeError(f"Shine resume upload failed: {errors}")
        self._save_shine_session()

    def update_profile_fields(self, proposal: dict) -> list[str]:
        if self.platform == "shine":
            return self._update_shine_profile_fields(proposal)
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
            self.pages["profile"],
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

    def _update_shine_profile_fields(self, proposal: dict) -> list[str]:
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        data = proposal.get("data")
        if not isinstance(data, dict):
            raise ValueError("The profile proposal has no valid data object.")

        sections = set(proposal.get("sections", []))
        print(
            "Shine's current editor does not support project or education "
            "updates. Certifications were left unchanged because the form "
            "requires validity details not extracted from the resume."
        )

        if self.page.url.rstrip("/") != self.pages["profile_edit"].rstrip("/"):
            self.prepare_profile_update()

        changed = []
        if "summary" in sections and data.get("summary"):
            if self._save_shine_summary(data["summary"]):
                changed.append("summary")

        if sections.intersection({"skills", "employment", "total_experience"}):
            updated_profile_fields = self._save_shine_work_profile(
                data.get("skills", [])
                if "skills" in sections
                else [],
                data.get("employment", [])
                if "employment" in sections
                else [],
                data.get("total_experience")
                if "total_experience" in sections
                else None,
            )
            changed.extend(updated_profile_fields)

        return changed

    def _save_shine_summary(self, summary: object) -> bool:
        if not isinstance(summary, str) or not summary.strip():
            return False

        heading = self.page.get_by_role(
            "heading",
            name="Profile Summary",
            exact=True,
        )
        if heading.count() != 1:
            raise RuntimeError(
                "Could not identify Shine's Profile Summary section."
            )

        section = heading.locator("xpath=..")
        action = section.get_by_role(
            "button",
            name=re.compile(r"^(add|update|edit)$", re.IGNORECASE),
        )
        if action.count() != 1:
            raise RuntimeError(
                "Could not find Shine's Profile Summary editor."
            )
        action.click(timeout=10000)

        summary_field = self.page.locator(
            "textarea[placeholder='Type your profile summary here...']"
        )
        if summary_field.count() != 1:
            raise RuntimeError(
                "Shine did not open the Profile Summary text editor."
            )
        summary_field.fill(summary.strip())

        save_button = self.page.get_by_role(
            "button",
            name="Save",
            exact=True,
        )
        if save_button.count() != 1:
            raise RuntimeError(
                "Could not find Shine's Profile Summary Save button."
            )
        try:
            with self.page.expect_response(
                lambda result: (
                    "/api/v4/candidate-summary/" in result.url
                    and result.request.method.upper() == "PUT"
                ),
                timeout=30000,
            ) as response_info:
                save_button.click(timeout=10000)
            response = response_info.value
        except PlaywrightError as error:
            raise RuntimeError(
                "Shine did not confirm the Profile Summary update."
            ) from error

        if not 200 <= response.status < 300:
            raise RuntimeError(
                "Shine rejected the Profile Summary update with HTTP "
                f"{response.status}."
            )
        return True

    def _save_shine_work_profile(
        self,
        skills: object,
        employment: object,
        total_experience: object,
    ) -> list[str]:
        update_button = self.page.get_by_role(
            "button",
            name="Update",
            exact=True,
        )
        if update_button.count() != 1:
            raise RuntimeError(
                "Could not find Shine's profile-details Update button."
            )
        update_button.click(timeout=10000)

        skill_values = self._clean_shine_skills(skills)
        existing_skill_items = self.page.locator(
            "li[class*='selectedSkill']"
        )
        existing_skills = {
            self._normalize_shine_skill(item.inner_text())
            for item in existing_skill_items.all()
        }
        added_skills = []
        if skill_values:
            skill_label = self.page.locator("label[for='skill']")
            if skill_label.count() != 1:
                raise RuntimeError("Could not find Shine's skill editor.")
            skill_input = skill_label.locator("xpath=..").locator("input")
            if skill_input.count() != 1:
                raise RuntimeError(
                    "Could not identify Shine's skill search input."
                )

            remaining_slots = max(0, 25 - len(existing_skills))
            skipped_for_limit = []
            for skill in skill_values:
                normalized = self._normalize_shine_skill(skill)
                if normalized in existing_skills:
                    continue
                if not remaining_slots:
                    skipped_for_limit.append(skill)
                    continue
                skill_input.fill(skill)
                self.page.wait_for_timeout(600)
                suggestion = self.page.get_by_text(
                    re.compile(
                        rf"^{re.escape(skill)}$",
                        re.IGNORECASE,
                    ),
                    exact=True,
                )
                visible_suggestions = [
                    candidate
                    for candidate in suggestion.all()
                    if candidate.is_visible()
                ]
                if not visible_suggestions:
                    print(
                        f"Shine did not offer '{skill}' as a selectable "
                        "skill; it was skipped."
                    )
                    skill_input.fill("")
                    continue
                try:
                    with self.page.expect_response(
                        lambda response: (
                            "/api/v2/candidate/" in response.url
                            and "/skills/" in urlparse(response.url).path
                            and response.request.method.upper() == "POST"
                        ),
                        timeout=30000,
                    ) as response_info:
                        visible_suggestions[-1].click(timeout=10000)
                    response = response_info.value
                except PlaywrightError as error:
                    raise RuntimeError(
                        f"Shine did not confirm adding the skill '{skill}'."
                    ) from error
                if not 200 <= response.status < 300:
                    raise RuntimeError(
                        f"Shine rejected the skill '{skill}' with HTTP "
                        f"{response.status}."
                    )
                self.page.wait_for_timeout(300)
                current_skills = {
                    self._normalize_shine_skill(item.inner_text())
                    for item in existing_skill_items.all()
                }
                if normalized not in current_skills:
                    raise RuntimeError(
                        f"Shine did not add the selected skill '{skill}'."
                    )
                existing_skills = current_skills
                added_skills.append(skill)
                remaining_slots -= 1
                skill_input.fill("")
            if skipped_for_limit:
                print(
                    "Shine's 25-skill limit was reached; skipped: "
                    + ", ".join(skipped_for_limit)
                )

        current_role = self._shine_current_employment(employment)
        changed_work_fields = []
        for selector, key, label in (
            ("#curr-comp", "company", "current company"),
            ("#curr-designation", "title", "current designation"),
        ):
            value = current_role.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            field = self.page.locator(selector)
            if field.count() != 1:
                raise RuntimeError(
                    f"Could not find Shine's {label} field."
                )
            if field.input_value().strip() != value.strip():
                field.fill(value.strip())
                changed_work_fields.append(label)

        total_experience_value = self._shine_total_experience_value(
            total_experience
        )
        if total_experience_value:
            field = self.page.locator("#total_experience")
            if field.count() != 1:
                raise RuntimeError(
                    "Could not find Shine's total-experience field."
                )
            if field.input_value().strip().casefold() != (
                total_experience_value.casefold()
            ):
                field.fill(total_experience_value)
                changed_work_fields.append("total experience")
        elif isinstance(total_experience, str) and total_experience.strip():
            print(
                "Shine total experience was left unchanged because the "
                "resume value was not in a supported years-only format."
            )

        if not added_skills and not changed_work_fields:
            return []

        if changed_work_fields:
            submit = self.page.get_by_role(
                "button",
                name="Submit",
                exact=True,
            )
            if submit.count() != 1:
                raise RuntimeError(
                    "Could not find Shine's profile-details Submit button."
                )
            try:
                with self.page.expect_response(
                    lambda response: (
                        "/api/v4/candidate-work-profile/"
                        in urlparse(response.url).path
                        and response.request.method.upper()
                        in {"POST", "PUT", "PATCH"}
                    ),
                    timeout=30000,
                ) as response_info:
                    submit.click(timeout=10000)
                response = response_info.value
            except PlaywrightError as error:
                raise RuntimeError(
                    "Shine did not confirm the profile details update."
                ) from error
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    "Shine rejected the profile details update with HTTP "
                    f"{response.status}."
                )

        updated = []
        if added_skills:
            updated.append(f"skills ({len(added_skills)} added)")
        updated.extend(changed_work_fields)
        return updated

    @staticmethod
    def _clean_shine_skills(skills: object) -> list[str]:
        if not isinstance(skills, list):
            raise ValueError("Proposed skills must be a list.")
        values = []
        seen = set()
        for skill in skills:
            if not isinstance(skill, str) or not skill.strip():
                continue
            normalized = CandidatePlatformBrowser._normalize_shine_skill(
                skill
            )
            if normalized not in seen:
                values.append(skill.strip())
                seen.add(normalized)
        return values

    @staticmethod
    def _normalize_shine_skill(skill: str) -> str:
        normalized = re.sub(r"\s+", " ", skill).strip()
        normalized = re.sub(r"\s*×\s*$", "", normalized)
        return normalized.casefold()

    @staticmethod
    def _shine_current_employment(employment: object) -> dict:
        if not isinstance(employment, list):
            raise ValueError("Proposed employment must be a list.")
        current_roles = [
            item
            for item in employment
            if isinstance(item, dict) and item.get("is_current") is True
        ]
        if len(current_roles) > 1:
            raise ValueError(
                "The resume proposal contains multiple current roles; "
                "Shine's current-work fields were left unchanged."
            )
        return current_roles[0] if current_roles else {}

    @staticmethod
    def _shine_total_experience_value(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*",
            value,
            re.IGNORECASE,
        )
        if not match:
            return None
        return f"{match.group(1)} Yrs"

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
                field.click(timeout=10000)
                search_fields = modal.locator(
                    "input:not([readonly]):not([type='hidden'])"
                )
                if search_fields.count() > 0:
                    search_field = search_fields.last
                    if search_field.is_visible():
                        search_field.fill(skill)
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
                        f"'{skill}' after opening its skill selector. Check "
                        "the profile manually; no additional skills were "
                        "saved."
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
        if title_option is not None:
            title_option.click(timeout=10000)
        elif title_field.input_value().strip().casefold() != title.casefold():
            raise RuntimeError(
                f"Foundit did not offer an exact job-title match for "
                f"'{title}'. No experience was saved."
            )
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
        context = self.context
        playwright = self.playwright
        owns_playwright = self._owns_playwright
        try:
            if context is not None:
                context.close()
        finally:
            try:
                if playwright is not None and owns_playwright:
                    playwright.stop()
            finally:
                self.context = None
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
        browser: ProfileFieldBrowser,
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
        if platform not in PROFILE_STATE_PLATFORMS:
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
        browser: ProfileFieldBrowser,
        resume_path: str | Path,
        proposal: dict,
        force: bool = False,
    ) -> list[str]:
        resume = Path(resume_path)
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        digest = self._file_hash(resume)
        if digest == self._previous_hash() and not force:
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
