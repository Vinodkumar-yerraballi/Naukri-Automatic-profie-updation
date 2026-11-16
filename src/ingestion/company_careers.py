"""Read public company career pages and extract structured job postings."""

from collections import deque
from html.parser import HTMLParser
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


USER_AGENT = "CompanyCareersJobSearch/1.0"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
JOB_LINK_PATTERN = re.compile(
    r"(?:^|[/_.-])(jobs?|careers?|openings?|positions?|vacancies|"
    r"requisitions?)(?:[/_.-]|$)|greenhouse|lever",
    re.IGNORECASE,
)


def _plain_text(value: str) -> str:
    if not value:
        return ""
    parser = _TextParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class _CareerPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_ld = []
        self.links = []
        self.meta = {}
        self.title_parts = []
        self.text_parts = []
        self.content_parts = []
        self._in_title = False
        self._ignored_tags = 0
        self._json_ld_depth = 0
        self._json_ld_parts = []
        self._current_link = None
        self._content_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            content_type = attributes.get("type", "").lower()
            if "ld+json" in content_type:
                self._json_ld_depth += 1
                self._json_ld_parts = []
            self._ignored_tags += 1
        elif tag in ("style", "noscript"):
            self._ignored_tags += 1
        else:
            if tag in ("main", "article") and self._content_depth == 0:
                self._content_depth = 1
            elif self._content_depth and tag not in VOID_TAGS:
                self._content_depth += 1

            if tag == "title":
                self._in_title = True
            elif tag == "meta":
                name = (
                    attributes.get("name")
                    or attributes.get("property")
                    or ""
                ).lower()
                if name and attributes.get("content"):
                    self.meta[name] = attributes["content"].strip()
            elif tag == "a" and attributes.get("href"):
                self._current_link = [
                    attributes["href"].strip(),
                    attributes.get("aria-label", ""),
                ]

    def handle_endtag(self, tag):
        if tag == "script":
            if self._json_ld_depth:
                self.json_ld.append("".join(self._json_ld_parts))
                self._json_ld_depth -= 1
            self._ignored_tags = max(0, self._ignored_tags - 1)
        elif tag in ("style", "noscript"):
            self._ignored_tags = max(0, self._ignored_tags - 1)
        else:
            if self._content_depth:
                self._content_depth -= 1
            if tag == "title":
                self._in_title = False
            elif tag == "a" and self._current_link:
                self.links.append(tuple(self._current_link))
                self._current_link = None

    def handle_data(self, data):
        if self._json_ld_depth:
            self._json_ld_parts.append(data)
        if self._current_link:
            self._current_link[1] += data
        if not self._ignored_tags:
            if self._in_title:
                self.title_parts.append(data)
            self.text_parts.append(data)
            if self._content_depth:
                self.content_parts.append(data)


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _is_job_posting(value):
    types = value.get("@type", [])
    if isinstance(types, str):
        types = [types]
    return any(str(item).rsplit("/", 1)[-1] == "JobPosting" for item in types)


def _first_text(value):
    if isinstance(value, str):
        return _plain_text(value)
    if isinstance(value, list):
        return ", ".join(filter(None, (_first_text(item) for item in value)))
    if isinstance(value, dict):
        return _first_text(
            value.get("name")
            or value.get("value")
            or value.get("text")
            or value.get("description")
            or ""
        )
    return ""


def _location_text(value):
    locations = value if isinstance(value, list) else [value]
    result = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address", location)
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            location_name = ", ".join(str(part) for part in parts if part)
        else:
            location_name = str(address)
        if location_name and location_name not in result:
            result.append(location_name)
    return ", ".join(result)


def _posting_from_json(value, page_url, company_name):
    organization = value.get("hiringOrganization", {})
    if isinstance(organization, dict):
        organization = organization.get("name", "")
    url = value.get("url") or value.get("mainEntityOfPage") or page_url
    if isinstance(url, dict):
        url = url.get("@id") or url.get("url") or page_url

    skills = value.get("skills") or value.get("qualifications") or []
    if isinstance(skills, str):
        skills = [item.strip() for item in re.split(r"[,;\n]", skills)]
    elif not isinstance(skills, list):
        skills = [skills]
    skills = [_first_text(item) for item in skills]

    education = value.get("educationRequirements") or []
    if not isinstance(education, list):
        education = [education]
    education = [_first_text(item) for item in education]

    location = _location_text(value.get("jobLocation"))
    if not location and str(value.get("jobLocationType", "")).upper() in (
        "TELECOMMUTE",
        "REMOTE",
    ):
        location = "Remote"

    return {
        "title": _first_text(value.get("title")) or "Not specified",
        "company": _first_text(organization) or company_name,
        "location": location or _first_text(value.get("jobLocationType")),
        "experience": _first_text(value.get("experienceRequirements")),
        "description": _plain_text(_first_text(value.get("description", ""))),
        "skills": [item for item in skills if item],
        "education": [item for item in education if item],
        "employment_type": _first_text(value.get("employmentType")),
        "posted": _first_text(value.get("datePosted")),
        "job_url": urljoin(page_url, str(url)),
    }


def _valid_http_url(url):
    parsed = urlsplit(url)
    return (
        parsed.scheme.lower() in ("http", "https")
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and "{" not in url
        and "}" not in url
    )


def parse_career_page(
    html,
    page_url,
    company_name,
    is_job_page=False,
    fallback_metadata=None,
):
    """Return structured postings and likely job-detail links from HTML."""
    parser = _CareerPageParser()
    parser.feed(html)

    jobs = []
    for block in parser.json_ld:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for item in _walk_json(data):
            if _is_job_posting(item):
                jobs.append(
                    _posting_from_json(item, page_url, company_name)
                )

    page_text = _plain_text(
        " ".join(parser.content_parts or parser.text_parts)
    )
    for job in jobs:
        if not job.get("description") and len(page_text) > 120:
            job["description"] = page_text

    links = []
    for href, label in parser.links:
        absolute_url = urldefrag(urljoin(page_url, href))[0]
        parsed = urlsplit(absolute_url)
        likely_job_link = (
            JOB_LINK_PATTERN.search(parsed.path)
            or re.search(
                r"\b(?:apply|view job|view details|open role|"
                r"see position|job opening)\b",
                label,
                re.IGNORECASE,
            )
        )
        if _valid_http_url(absolute_url) and likely_job_link and (
            absolute_url != page_url
        ):
            links.append(absolute_url)

    if is_job_page and not jobs:
        fallback_metadata = fallback_metadata or {}
        title = (
            _plain_text(" ".join(parser.title_parts))
            or fallback_metadata.get("title", "")
        )
        description = page_text
        if len(description) <= 120:
            description = (
                parser.meta.get("description")
                or parser.meta.get("og:description")
                or description
            )
        if title and len(description) > 120:
            jobs.append({
                "title": title,
                "company": company_name,
                "location": fallback_metadata.get("location", ""),
                "experience": fallback_metadata.get("experience", ""),
                "description": description,
                "skills": fallback_metadata.get("skills", []),
                "education": fallback_metadata.get("education", []),
                "employment_type": fallback_metadata.get(
                    "employment_type", ""
                ),
                "posted": fallback_metadata.get("posted", ""),
                "job_url": page_url,
            })

    return jobs, links


class CompanyCareersScraper:
    """Crawl a bounded set of public career pages while honoring robots.txt."""

    def __init__(
        self,
        request_delay_seconds=2,
        max_pages_per_company=10,
        max_jobs_per_company=50,
        timeout_seconds=20,
    ):
        self.request_delay_seconds = max(0, float(request_delay_seconds))
        self.max_pages_per_company = max(1, int(max_pages_per_company))
        self.max_jobs_per_company = max(1, int(max_jobs_per_company))
        self.timeout_seconds = max(1, int(timeout_seconds))
        self._last_request_time = None
        self._robots_cache = {}

    def _wait(self):
        if self._last_request_time is not None:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.request_delay_seconds:
                time.sleep(self.request_delay_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def _robots_allowed(self, url):
        parsed = urlsplit(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        if robots_url not in self._robots_cache:
            self._wait()
            request = Request(robots_url, headers={"User-Agent": USER_AGENT})
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    content = response.read(512 * 1024).decode(
                        "utf-8", errors="replace"
                    )
                parser = RobotFileParser(robots_url)
                parser.parse(content.splitlines())
                self._robots_cache[robots_url] = parser
            except HTTPError as error:
                if error.code == 404:
                    parser = RobotFileParser(robots_url)
                    parser.parse([])
                    self._robots_cache[robots_url] = parser
                else:
                    raise RuntimeError(
                        f"Could not read robots.txt for {url}: HTTP "
                        f"{error.code}"
                    ) from error
            except (OSError, URLError) as error:
                raise RuntimeError(
                    f"Could not read robots.txt for {url}: {error}"
                ) from error
        return self._robots_cache[robots_url].can_fetch(USER_AGENT, url)

    def _fetch(self, url):
        if not _valid_http_url(url):
            raise ValueError(f"Unsupported career page URL: {url}")
        if not self._robots_allowed(url):
            raise RuntimeError(f"robots.txt disallows fetching {url}")

        self._wait()
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "")
                if content_type and "html" not in content_type.lower():
                    return None
                html = response.read(MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError) as error:
            raise RuntimeError(f"Could not fetch {url}: {error}") from error
        if len(html) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"Career page is larger than 5 MB: {url}")
        return html.decode("utf-8", errors="replace")

    def scrape_company(self, company_name, careers_url):
        if not _valid_http_url(careers_url):
            raise ValueError(
                f"Invalid careers URL for {company_name}: {careers_url}"
            )

        queue = deque([(urldefrag(careers_url)[0], False)])
        visited = set()
        jobs_by_url = {}
        pages_read = 0

        while queue and pages_read < self.max_pages_per_company:
            page_url, is_job_page = queue.popleft()
            if page_url in visited:
                continue
            visited.add(page_url)
            html = self._fetch(page_url)
            pages_read += 1
            if html is None:
                continue

            page_jobs, links = parse_career_page(
                html,
                page_url,
                company_name,
                is_job_page=is_job_page,
            )
            for job in page_jobs:
                job["company"] = job.get("company") or company_name
                job["job_url"] = urldefrag(
                    urljoin(page_url, job.get("job_url", page_url))
                )[0]
                key = job["job_url"].lower()
                if key not in jobs_by_url:
                    jobs_by_url[key] = job
                if len(jobs_by_url) >= self.max_jobs_per_company:
                    break

            for link in links:
                if link not in visited and len(queue) + pages_read < (
                    self.max_pages_per_company
                ):
                    queue.append((link, True))
            if len(jobs_by_url) >= self.max_jobs_per_company:
                break

        return list(jobs_by_url.values()), pages_read

    def scrape_job_urls(self, company_name, job_records):
        """Fetch supplied job-detail links and retain per-link failures."""
        jobs_by_url = {}
        errors = []
        pages_read = 0

        for record in job_records:
            job_url = str(record.get("url", "")).strip()
            # The supplied Accenture export left the locale token as {0}.
            # The configured company careers page is the India English site.
            if company_name.casefold() == "accenture" and "{0}" in job_url:
                job_url = job_url.replace("{0}", "in-en")
            if not _valid_http_url(job_url):
                errors.append({
                    "company": company_name,
                    "job_url": job_url,
                    "error": "Invalid or unsupported job URL.",
                })
                continue

            job_url = urldefrag(job_url)[0]
            key = job_url.lower()
            if key in jobs_by_url:
                continue
            try:
                html = self._fetch(job_url)
                pages_read += 1
                if html is None:
                    errors.append({
                        "company": company_name,
                        "job_url": job_url,
                        "error": "The URL did not return an HTML page.",
                    })
                    continue
                page_jobs, _ = parse_career_page(
                    html,
                    job_url,
                    company_name,
                    is_job_page=True,
                    fallback_metadata=record,
                )
                if not page_jobs:
                    errors.append({
                        "company": company_name,
                        "job_url": job_url,
                        "error": (
                            "No job description was readable from the page."
                        ),
                    })
                    continue
                job = page_jobs[0]
                job["company"] = company_name
                job["job_url"] = job_url
                job["title"] = record.get("title") or job.get(
                    "title",
                    "Not specified",
                )
                job["location"] = (
                    job.get("location") or record.get("location", "")
                )
                jobs_by_url[key] = job
            except (RuntimeError, ValueError, TypeError) as error:
                errors.append({
                    "company": company_name,
                    "job_url": job_url,
                    "error": f"{type(error).__name__}: {error}",
                })

        return list(jobs_by_url.values()), pages_read, errors
