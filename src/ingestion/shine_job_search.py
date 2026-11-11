import re
from urllib.parse import quote, urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.matching.freshness_matcher import FreshnessMatcher


class ShineJobSearch:
    """Search public Shine listings with a verifiable posting age and JD."""

    BASE_URL = "https://www.shine.com"
    CARD_SELECTOR = "article[itemprop='itemListElement']"
    TITLE_SELECTOR = ".result-card_hit__tL8tN"
    COMPANY_SELECTOR = ".result-card_company__V6mN_"
    POSTED_SELECTOR = ".result-card_posted__i_x9C"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900}
        )
        self.page = self.context.new_page()

    def search_jobs(
        self,
        role: str,
        location: str,
        posted_within_hours: int,
        max_results: int | None = None,
    ) -> list[dict]:
        if self.page is None or self.context is None:
            raise RuntimeError("Shine job-search browser is not started.")
        if max_results is not None and max_results <= 0:
            return []

        search_url = self._search_url(role, location)
        response = self.page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        status = getattr(response, "status", None) if response else None
        if status is not None and status >= 400:
            raise RuntimeError(
                f"Shine search returned HTTP {status} for {role} in "
                f"{location}."
            )
        if self.page.title().casefold() == "access denied":
            raise RuntimeError(
                "Shine denied access to public job search. No access "
                "controls were bypassed."
            )

        cards = self.page.locator(self.CARD_SELECTOR)
        if cards.count() == 0:
            body = self.page.locator("body").inner_text().casefold()
            if "jobs found" in body or "no jobs" in body:
                return []
            raise RuntimeError(
                "Shine's public job-card layout changed; no results were "
                "processed."
            )

        freshness = FreshnessMatcher()
        jobs = []
        seen_urls = set()
        for card in cards.all():
            title = self._first_text(card, self.TITLE_SELECTOR)
            company = self._first_text(card, self.COMPANY_SELECTOR)
            posted = self._first_text(card, self.POSTED_SELECTOR)
            link = card.locator(self.TITLE_SELECTOR)
            href = link.get_attribute("href") if link.count() else None
            if not title or not company or not href:
                continue
            job_url = urljoin(self.BASE_URL, href)
            parsed_url = urlparse(job_url)
            if (
                parsed_url.scheme != "https"
                or parsed_url.hostname != "www.shine.com"
                or not parsed_url.path.startswith("/jobs/")
            ):
                continue
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            if not freshness.is_within_last_hours(
                posted,
                max_hours=posted_within_hours,
            ):
                print(
                    "Skipping Shine listing with unknown or older posting "
                    f"age: {title} ({posted or 'age unavailable'})."
                )
                continue

            card_text = " ".join(card.inner_text().split())
            experience_match = re.search(
                r"\b\d+(?:\.\d+)?\s*(?:to|-)\s*\d+(?:\.\d+)?\s*"
                r"(?:yrs?|years?)\b",
                card_text,
                re.IGNORECASE,
            )
            description = self._get_job_description(job_url)
            if not description:
                print(
                    "Skipping Shine listing because a full job description "
                    f"could not be verified: {title} ({job_url})."
                )
                continue

            jobs.append(
                {
                    "job_url": job_url,
                    "title": title,
                    "company": company,
                    "location": self._find_location(card_text, location),
                    "experience": (
                        experience_match.group(0)
                        if experience_match
                        else ""
                    ),
                    "posted": posted,
                    "description": description,
                    "description_is_complete": True,
                }
            )
            if max_results is not None and len(jobs) >= max_results:
                break
        return jobs

    @staticmethod
    def _search_url(role: str, location: str) -> str:
        role_slug = re.sub(r"\s+", "-", role.strip().lower())
        location_slug = re.sub(r"\s+", "-", location.strip().lower())
        if not role_slug or not location_slug:
            raise ValueError("A Shine role and location are required.")
        return (
            f"{ShineJobSearch.BASE_URL}/job-search/"
            f"{quote(role_slug, safe='-')}-jobs-in-"
            f"{quote(location_slug, safe='-')}"
        )

    def _get_job_description(self, job_url: str) -> str:
        if self.context is None:
            raise RuntimeError("Shine job-search browser is not started.")
        detail_page = self.context.new_page()
        try:
            response = detail_page.goto(
                job_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            status = getattr(response, "status", None) if response else None
            if status is not None and status >= 400:
                raise RuntimeError(
                    f"Shine job detail returned HTTP {status}: {job_url}"
                )
            text = detail_page.locator("body").inner_text()
            return self._extract_job_description(text)
        finally:
            detail_page.close()

    @staticmethod
    def _extract_job_description(text: str) -> str:
        start = re.search(r"\bJob Description\b", text, re.IGNORECASE)
        if start is None:
            return ""
        content = text[start.end():]
        end = re.search(
            r"\n\s*(?:Industry|Department)\s*(?:\n|$)",
            content,
            re.IGNORECASE,
        )
        if end is not None:
            content = content[:end.start()]
        description = "\n".join(
            line.strip() for line in content.splitlines() if line.strip()
        ).strip()
        return description if len(description) >= 100 else ""

    @staticmethod
    def _first_text(card, selector: str) -> str:
        locator = card.locator(selector)
        for item in locator.all():
            if item.is_visible():
                text = " ".join(item.inner_text().split())
                if text:
                    return text
        return ""

    @staticmethod
    def _find_location(card_text: str, requested_location: str) -> str:
        aliases = {
            "bangalore": ("bangalore", "bengaluru"),
            "bengaluru": ("bangalore", "bengaluru"),
            "remote": ("remote", "work from home"),
        }
        terms = aliases.get(
            requested_location.casefold(),
            (requested_location.casefold(),),
        )
        for line in card_text.split():
            normalized = line.strip(" ,.;()[]").casefold()
            if normalized in terms:
                return requested_location
        return ""

    def close(self) -> None:
        browser = self.browser
        playwright = self.playwright
        try:
            if browser is not None:
                browser.close()
        finally:
            if playwright is not None:
                playwright.stop()
