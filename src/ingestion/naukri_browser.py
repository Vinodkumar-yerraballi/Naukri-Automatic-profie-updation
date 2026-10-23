from playwright.sync_api import sync_playwright
from pathlib import Path
import re
from urllib.parse import quote_plus


class NaukriBrowser:
    """
    Browser-based Naukri job collector.

    Responsibilities:
    - Open Naukri
    - Search for jobs
    - Read visible job listings
    - Return normalized job information

    CAPTCHA/OTP/security challenges require manual action.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None

    def start(self):
        """Start the Playwright browser."""

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        self.page = self.browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

    def start_persistent(self, user_data_dir: str | Path):
        """Start Chromium with a persistent local browser session."""
        profile_dir = Path(user_data_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir.resolve()),
            headless=self.headless,
            viewport={"width": 1440, "height": 900},
        )
        self.page = self.browser.new_page()

    def open_naukri(self):
        """Open the Naukri website."""

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        self.page.goto(
            "https://www.naukri.com/",
            wait_until="domcontentloaded",
            timeout=60000
        )

    def setup_naukri_login(self):
        """Open Naukri's login page for a user to sign in manually."""
        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start_persistent() first."
            )
        self.page.goto(
            "https://www.naukri.com/nlogin/login",
            wait_until="domcontentloaded",
            timeout=60000,
        )

    def update_profile_resume(self, resume_path: str | Path) -> None:
        """Upload a resume to the signed-in Naukri profile and verify it."""
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        resume = Path(resume_path).resolve()
        if not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        self.page.goto(
            "https://www.naukri.com/mnjuser/profile",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        self.page.wait_for_timeout(2000)

        if self.detect_security_challenge():
            raise RuntimeError(
                "Naukri requested a security check. Complete it manually "
                "and run the profile update again."
            )

        current_url = self.page.url.lower()
        page_text = self.page.locator("body").inner_text().lower()
        if "login" in current_url or "login to naukri" in page_text:
            raise RuntimeError(
                "Naukri is not signed in in the saved browser profile. "
                "Run `python main.py --setup-naukri-session` and sign in "
                "manually."
            )

        upload_control = self.page.locator(
            "input[type='file'][accept*='.pdf']"
        )
        if upload_control.count() == 0:
            upload_link = self.page.get_by_text(
                re.compile(r"upload resume|update resume", re.IGNORECASE)
            )
            if upload_link.count() > 0:
                upload_link.first.click(timeout=10000)
                self.page.wait_for_timeout(1000)
            upload_control = self.page.locator("input[type='file']")

        if upload_control.count() == 0:
            raise RuntimeError(
                "Could not find the resume upload control on the Naukri "
                "profile page; no file was uploaded."
            )

        upload_control.first.set_input_files(str(resume))
        self.page.wait_for_timeout(2000)

        save_button = self.page.get_by_role(
            "button",
            name=re.compile(
                r"(upload|update|save).*resume|resume.*(upload|update|save)",
                re.IGNORECASE,
            ),
        )
        if save_button.count() > 0 and save_button.first.is_visible():
            save_button.first.click(timeout=10000)

        self.page.wait_for_timeout(5000)
        confirmation_text = self.page.locator("body").inner_text().lower()
        success_phrases = (
            "resume uploaded",
            "resume updated",
            "successfully uploaded",
            "successfully updated",
        )
        if (
            resume.name.lower() not in confirmation_text
            and not any(
                phrase in confirmation_text for phrase in success_phrases
            )
        ):
            raise RuntimeError(
                "The profile page did not confirm the resume upload. "
                "Check your Naukri profile manually before retrying."
            )

    def search_jobs(
        self,
        role: str,
        location: str = "",
        posted_within_hours: int | None = None,
    ):
        """
        Search Naukri for a role and location.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        role_query = quote_plus(role)

        if location:
            location_query = quote_plus(location)

            url = (
                "https://www.naukri.com/"
                f"{role_query}-jobs-in-{location_query}"
            )

        else:
            url = (
                "https://www.naukri.com/"
                f"{role_query}-jobs"
            )

        if posted_within_hours is not None:
            if posted_within_hours <= 0:
                raise ValueError("posted_within_hours must be positive.")
            if posted_within_hours <= 24:
                url += "?jobAge=1"

        print("\nOpening search URL:")
        print(url)

        self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Allow dynamically loaded job results to render.
        self.page.wait_for_timeout(5000)

        print("\nCurrent URL:")
        print(self.page.url)

        print("\nPage title:")
        print(self.page.title())

        return self.page

    def get_page_title(self) -> str:
        """Return the current browser page title."""

        if self.page is None:
            return ""

        return self.page.title()

    def get_current_url(self) -> str:
        """Return the current browser URL."""

        if self.page is None:
            return ""

        return self.page.url

    def get_visible_text(self) -> str:
        """Return visible text from the current page."""

        if self.page is None:
            return ""

        return self.page.locator("body").inner_text()

    def detect_security_challenge(self) -> bool:
        """
        Detect common CAPTCHA/security verification pages.
        """

        if self.page is None:
            return False

        page_text = self.page.locator("body").inner_text().lower()

        security_keywords = [
            "captcha",
            "recaptcha",
            "hcaptcha",
            "verify you are human",
            "verification required",
            "security check",
            "enter otp",
            "one time password"
        ]

        for keyword in security_keywords:
            if keyword in page_text:
                return True

        return False

    def get_job_cards(self) -> list:
        """
        Extract visible job cards from the current search page.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        # Wait for the page to render.
        self.page.wait_for_timeout(7000)

        # Detect security challenges first.
        if self.detect_security_challenge():
            print(
                "Security challenge detected. "
                "Manual action is required."
            )
            return []

        selectors = [
            "div.srp-jobtuple-wrapper",
            "article.jobTuple",
            "div.jobTuple",
            "article"
        ]

        job_cards = []

        for selector in selectors:

            try:

                cards = self.page.locator(selector)

                count = cards.count()

                if count > 0:

                    print(
                        f"Found {count} elements using selector: "
                        f"{selector}"
                    )
                    print(f"\nDEBUG: Processing {count} cards using selector: {selector}")

                    for index in range(count):

                        try:

                            card = cards.nth(index)

                            # ------------------------------------------------
                            # TEMPORARY DEBUG
                            # Print complete text of each job card.
                            # This will help us identify the current
                            # Naukri "posted" field.
                            # ------------------------------------------------



                            title_locator = card.locator("a.title")
                            company_locator = card.locator("a.comp-name")
                            location_locator = card.locator("span.locWdth")
                            experience_locator = card.locator("span.expwdth")
                            posted_locator = card.locator("span.job-post-day")

                            # ------------------------------------------------
                            # Job fields
                            # ------------------------------------------------

                            title = ""
                            company = ""
                            location = ""
                            experience = ""
                            posted = ""
                            job_url = ""

                            # ------------------------------------------------
                            # Title
                            # ------------------------------------------------

                            title_locator = card.locator(
                                "a.title"
                            )

                            if title_locator.count() > 0:

                                title = (
                                    title_locator.first.inner_text()
                                )

                                href = (
                                    title_locator.first.get_attribute(
                                        "href"
                                    )
                                )

                                if href:
                                    job_url = href

                            # ------------------------------------------------
                            # Company
                            # ------------------------------------------------

                            # ------------------------------------------------
# Company
# ------------------------------------------------

                            company_locator = card.locator("a.comp-name")

                            if company_locator.count() > 0:
                                company = company_locator.first.inner_text().strip()

                                if "synapse" in company.lower():
                                    print("\n========== SYNAPSE CARD HTML ==========")
                                    print(card.evaluate("(element) => element.outerHTML"))
                                    print("========== END SYNAPSE CARD HTML ==========\n")

                            # ------------------------------------------------
                            # Location
                            # ------------------------------------------------
                            location_locator = card.locator("span.locWdth")

                            if location_locator.count() > 0:
                                location = location_locator.first.inner_text().strip()

                            if not location:
                                location_locator = card.locator("span.locWdth2")

                                if location_locator.count() > 0:
                                    location = location_locator.first.inner_text().strip()

                            if not location:
                                location = card.get_attribute("data-location") or ""
                            # ------------------------------------------------
                            # Experience
                            # ------------------------------------------------

                            experience_locator = card.locator("span.expwdth")

                            if experience_locator.count() > 0:
                                experience = experience_locator.first.inner_text().strip()

                            if not experience:
                                experience = card.get_attribute("data-experience") or ""

                            # ------------------------------------------------
                            # Posted time/date
                            # ------------------------------------------------

                            posted_locator = card.locator(
                                "span.job-post-day"
                            )

                            if posted_locator.count() > 0:

                                posted = (
                                    posted_locator.first.inner_text()
                                )

                            # ------------------------------------------------
                            # Save job
                            # ------------------------------------------------

                            if title or job_url:

                                job_cards.append(
                                    {
                                        "title": title.strip(),
                                        "company": company.strip(),
                                        "location": location.strip(),
                                        "experience": experience.strip(),
                                        "posted": posted.strip(),
                                        "job_url": job_url,
                                        "source": "Naukri"
                                    }
                                )

                        except Exception as error:

                            print(
                            f"\n========== CARD EXTRACTION ERROR =========="
                            )
                            print(f"Card index: {index}")
                            print(f"Error type: {type(error).__name__}")
                            print(f"Error: {error}")
                            print("============================================")

                    if job_cards:
                        break

            except Exception as error:

                print(
                    f"Selector failed: {selector}"
                )

                print(error)

        return job_cards

    def get_job_description(self, job_url: str) -> str:
        """
        Open an individual Naukri job page and extract
        the visible job description.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        if not job_url:
            return ""

        print("\nOpening job URL:")
        print(job_url)

        try:

            self.page.goto(
                job_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            self.page.wait_for_timeout(4000)

            print("\nJob page URL:")
            print(self.page.url)

            print("\nJob page title:")
            print(self.page.title())

            # Security check
            if self.detect_security_challenge():

                print(
                    "\nSecurity challenge detected."
                )

                print(
                    "Manual action is required."
                )

                return ""

            # Get all visible page text.
            body = self.page.locator("body")

            if body.count() == 0:
                return ""

            page_text = body.inner_text()

            print(
                "\nPage text length:",
                len(page_text)
            )

            # Print a limited preview for diagnosis.
            print(
                "\n========== JOB PAGE PREVIEW =========="
            )

            print(page_text[:5000])

            # Current/common Naukri description selectors.
            selectors = [
                "div.dang-inner-html",
                "div.styles_job-desc-container__tx3BB",
                "div.job-desc",
                "section.job-desc",
                "[class*='job-desc']",
                "[class*='jobDescription']"
            ]

            for selector in selectors:

                try:

                    locator = self.page.locator(
                        selector
                    )

                    count = locator.count()

                    if count > 0:

                        print(
                            f"\nFound description selector: "
                            f"{selector}"
                        )

                        text = locator.first.inner_text()

                        if text.strip():

                            return text.strip()

                except Exception as error:

                    print(
                        f"Selector failed: {selector}"
                    )

                    print(error)

            print(
                "\nNo known description selector matched."
            )

            return ""

        except Exception as error:

            print(
                "\nCould not open/extract job description."
            )

            print(
                type(error).__name__,
                error
            )

            return ""

    def debug_job_page(self) -> dict:
        """
        Collect basic information about the current job page
        to help identify the current Naukri DOM structure.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        result = {
            "url": self.page.url,
            "title": self.page.title(),
            "body_text_length": 0,
            "body_text_preview": "",
            "div_count": 0,
            "section_count": 0
        }

        try:

            body_text = self.page.locator(
                "body"
            ).inner_text()

            result["body_text_length"] = len(body_text)

            result["body_text_preview"] = body_text[:5000]

            result["div_count"] = self.page.locator(
                "div"
            ).count()

            result["section_count"] = self.page.locator(
                "section"
            ).count()

        except Exception as error:

            result["error"] = str(error)

        return result

    def extract_job_details(
        self,
        job: dict
    ) -> dict:
        """
        Open an individual Naukri job page and extract
        the complete job details.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser is not started. Call start() first."
            )

        job_url = job.get("job_url", "")

        if not job_url:
            return job

        print("\nOpening job:")
        print(job_url)

        try:

            self.page.goto(
                job_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            self.page.wait_for_timeout(4000)

            # Check for CAPTCHA / OTP / security challenge
            if self.detect_security_challenge():

                print(
                    "Security challenge detected."
                )

                print(
                    "Manual action is required."
                )

                job["security_challenge"] = True

                return job

            job["security_challenge"] = False

            # -----------------------------------------
            # Job description
            # -----------------------------------------

            description = ""

            description_selectors = [
                "[class*='job-desc']",
                "div.dang-inner-html",
                "div.job-desc",
                "section.job-desc"
            ]

            for selector in description_selectors:

                locator = self.page.locator(
                    selector
                )

                if locator.count() > 0:

                    text = locator.first.inner_text()

                    if text.strip():

                        description = text.strip()

                        break

            job["job_description"] = description

            # -----------------------------------------
            # Employment type
            # -----------------------------------------

            page_text = self.page.locator(
                "body"
            ).inner_text()

            employment_type = ""

            for line in page_text.splitlines():

                line = line.strip()

                if line.startswith(
                    "Employment Type:"
                ):

                    employment_type = (
                        line.replace(
                            "Employment Type:",
                            ""
                        ).strip()
                    )

                    break

            job["employment_type"] = employment_type

            # -----------------------------------------
            # Education
            # -----------------------------------------

            education = []

            education_keywords = [
                "UG:",
                "PG:"
            ]

            lines = page_text.splitlines()

            for line in lines:

                line = line.strip()

                for keyword in education_keywords:

                    if line.startswith(keyword):

                        value = (
                            line.replace(
                                keyword,
                                ""
                            ).strip()
                        )

                        if value:
                            education.append(value)

            job["education"] = education

            # -----------------------------------------
            # Update experience if available
            # -----------------------------------------

            if not job.get("experience"):

                import re

                experience_pattern = (
                    r"\b(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)\b"
                    r"|\b(\d+)\s*\+\s*(?:years?|yrs?)\b"
                )

                experience_match = re.search(
                    experience_pattern,
                    page_text,
                    re.IGNORECASE
                )

                if experience_match:

                    if experience_match.group(1) and experience_match.group(2):
                        job["experience"] = (
                            f"{experience_match.group(1)}-"
                            f"{experience_match.group(2)} years"
                        )

                    elif experience_match.group(3):
                        job["experience"] = (
                            f"{experience_match.group(3)}+ years"
                        )

            # -----------------------------------------
            # Return normalized job
            # -----------------------------------------

            return job

        except Exception as error:

            print(
                "\nCould not extract job details."
            )

            print(
                type(error).__name__,
                error
            )

            job["extraction_error"] = str(error)

            return job

    def close(self):
        """Close browser and Playwright."""

        if self.browser:

            self.browser.close()

            self.browser = None

        if self.playwright:

            self.playwright.stop()

            self.playwright = None

        self.page = None