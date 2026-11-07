from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


class InstahyreBrowser:
    """Search public Instahyre listings and return visible job-card data."""

    SEARCH_URL = "https://www.instahyre.com/search-jobs/"
    JOB_CARD_SELECTOR = "a.row.text-link"
    FILTER_OPTIONS_SELECTOR = (
        ".selectize-dropdown [data-selectable], "
        ".selectize-dropdown-content [data-selectable], "
        "[role='option']"
    )
    LOCATION_ALIASES = {"remote": "Work From Home"}

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    def start(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )
        self.page = self.browser.new_page(
            viewport={"width": 1440, "height": 900}
        )

    def search_jobs(self, role: str, location: str) -> list[dict]:
        if self.page is None:
            raise RuntimeError("Browser is not started.")

        response = self.page.goto(
            self.SEARCH_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        response_status = (
            getattr(response, "status", None) if response is not None else None
        )
        if response_status is not None and response_status >= 400:
            raise RuntimeError(
                f"Instahyre search page returned HTTP {response_status}."
            )

        title_field = self.page.locator(
            "#skills-drop-select-job-search-selectized"
        )
        location_field = self.page.locator("#locations-selectized")
        for field in (title_field, location_field):
            field.wait_for(state="visible", timeout=30000)
        self._check_security_challenge()
        title_field.fill(role)
        search_button = self.page.locator("button.skills-search-btn")
        if search_button.count() != 1 or not search_button.is_visible():
            raise RuntimeError(
                "Could not identify Instahyre's job-title Search button."
            )
        search_button.click(timeout=10000)
        self.page.wait_for_timeout(1000)
        self._select_filter(
            "#locations-selectized",
            location,
            "location",
        )
        search_button = self.page.locator("button.skills-search-btn")
        if search_button.count() != 1 or not search_button.is_visible():
            raise RuntimeError(
                "Could not identify Instahyre's Search button after "
                "selecting the location."
            )
        search_button.click(timeout=10000)
        self.page.wait_for_timeout(1200)
        self._check_security_challenge()

        jobs = []
        seen_urls = set()
        for card in self.page.locator(self.JOB_CARD_SELECTOR).all():
            if not card.is_visible():
                continue
            job = self._extract_job_card(card)
            if job and job["job_url"] not in seen_urls:
                jobs.append(job)
                seen_urls.add(job["job_url"])
        return jobs

    def _select_filter(
        self,
        selector: str,
        value: str,
        field_name: str,
    ) -> None:
        field = self.page.locator(selector)
        if field.count() != 1:
            raise RuntimeError(
                f"Could not identify Instahyre's {field_name} search field "
                f"({selector})."
            )

        filter_value = value
        if field_name.casefold() == "location":
            filter_value = self.LOCATION_ALIASES.get(
                value.casefold(),
                value,
            )

        field.fill(filter_value)
        self.page.wait_for_timeout(500)
        matching_options = []
        option_texts = []
        for option in self.page.locator(
            self.FILTER_OPTIONS_SELECTOR
        ).all():
            if not option.is_visible():
                continue
            text = " ".join(option.inner_text().split())
            if text and text not in option_texts:
                option_texts.append(text)
            matches_exactly = text.casefold() == filter_value.casefold()
            starts_with_filter = text.casefold().startswith(
                filter_value.casefold()
            )
            if matches_exactly or starts_with_filter:
                matching_options.append(option)

        if not matching_options:
            examples = ", ".join(option_texts[:5]) or "none visible"
            requested_value = (
                f"'{filter_value}' (mapped from '{value}')"
                if filter_value != value
                else f"'{value}'"
            )
            raise RuntimeError(
                f"Instahyre did not offer {requested_value} as a "
                f"{field_name} filter. "
                f"Visible options: {examples}."
            )

        matching_options[0].click(timeout=10000)

    def _check_security_challenge(self) -> None:
        body = self.page.locator("body").inner_text().casefold()
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
                "Instahyre requested a security check. Complete it manually "
                "in the browser, then run the search again."
            )

    def _extract_job_card(self, card) -> dict | None:
        href = card.get_attribute("href")
        if not href:
            return None
        job_url = urljoin(self.SEARCH_URL, href)
        parsed_url = urlparse(job_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "www.instahyre.com"
        ):
            return None

        employer_job_name = self._first_text(card, ".employer-job-name")
        if " - " not in employer_job_name:
            raise RuntimeError(
                "Instahyre changed its job-card title format; expected "
                "'Company - Job title' but received "
                f"{employer_job_name!r}."
            )
        company, title = employer_job_name.split(" - ", 1)
        company = company.strip()
        title = title.strip()
        if not company or not title:
            return None

        location = self._first_text(card, ".employer-chips-location")
        card_text = " ".join(card.inner_text().split())

        skills = self._first_text(card, ".job-skills")
        description = " ".join(
            part for part in (card_text, skills) if part
        )
        return {
            "job_url": job_url,
            "title": title,
            "company": company,
            "location": location,
            "experience": "",
            "description": description,
        }

    @staticmethod
    def _first_text(card, selector: str) -> str:
        locator = card.locator(selector)
        for item in locator.all():
            if item.is_visible():
                text = " ".join(item.inner_text().split())
                if text:
                    return text
        return ""

    def close(self) -> None:
        browser = self.browser
        playwright = self.playwright
        try:
            if browser is not None:
                browser.close()
        finally:
            try:
                if playwright is not None:
                    playwright.stop()
            finally:
                self.browser = None
                self.playwright = None
                self.page = None
