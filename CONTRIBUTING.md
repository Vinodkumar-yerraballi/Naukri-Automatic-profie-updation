# Contributing to Naukri Resume Automation

Thank you for wanting to help! This project automates Naukri profile updates and job searching via Playwright. Below are the guidelines for contributing.

## Table of Contents
1. [Code of Conduct](#code-of-conduct)
2. [Project Structure](#project-structure)
3. [Adding a New Platform Adapter](#adding-a-new-platform-adapter)
4. [Running Tests](#running-tests)
5. [Version & Release Process](#version--release-process)

---

## Code of Conduct
Please be respectful when raising issues or submitting pull requests. This project aims to help job-seekers; hostile or unhelpful behavior will not be tolerated.

## Project Structure
```
src/
├── ingestion/       # Platform scrapers (Naukri, Shine, Foundit, etc.)
├── matching/        # Scoring, freshness, education matching
├── profile/         # Profile updaters per platform
├── database/        # SQLite job repository
├── pipelines/       # Daily scheduler, job pipeline
└── utils/           # Shared helpers, logging
scripts/           # CLI commands (export_jobs_excel, etc.)
tests/             # pytest suite (12 tests, all passing)
LICENSE
README.md
```

## Adding a New Platform Adapter
To add support for a new job portal (e.g., LinkedIn, CoCubes):

1. **Create a new file** in `src/ingestion/`, e.g. `linkedin_browser.py`.
2. **Implement the minimal interface**:
   - `class LinkedInBrowser:` with `start()`, `search_jobs(role, location)`, `close()`.
   - The methods must mirror the existing Naukri/Shine APIs so the main pipeline (`main.py`) can call them identically.
3. **Register the adapter** in `src/ingestion/__init__.py`:
   ```python
   ADAPTERS = {
       "naukri": NaukriBrowser,
       "shine": ShineJobSearch,
       "foundit": FounditBrowser,  # if you add one
       "linkedin": LinkedInBrowser,
   }
   ```
4. **Update `main.py`** if you add new CLI flags (e.g., `--search-linkedin`).
5. **Add tests** in `tests/` following the existing patterns.

**Key selectors to discover** (capture DOM snapshots with your browser):
- Profile page URL
- Resume upload control selector
- Keyword/skill input selector
- Employment/project section navigators
- Save/submit button selectors

*Tip: Run `python -c "from src.ingestion.naukri_browser import NaukriBrowser; ..."` and inspect the live DOM with F12. Screenshots are welcome in the PR.*

## Running Tests
```bash
cd C:\Users\vinod\OneDrive\Desktop\Naukri-Automatic-profie-updation
.\.venv\Scripts\python.exe -m pytest -q tests/
```
All 12 tests must pass before a PR is merged. New tests should cover the new adapter's core paths (happy path + at least one error path).

## Version & Release Process
1. Bump the version in `config/config.yaml` (or add a `__version__.py` at repo root).
2. Tag the commit: `git tag v1.0.0 && git push origin v1.0.0`.
3. Draft a GitHub Release with the changelog.
4. Update the GitHub Actions workflow (`.github/workflows/daily-tests.yml`) if you added new test modules.

---

## Need Help?
- Open a discussion on GitHub instead of an issue for "I'm stuck on X."
- Ask in the `#job-automation` channel (or similar) if you have broader questions.
- If you're adding a platform, start by forking the repo, adding your adapter, and submitting a PR. The maintainer will review the selectors and tests.

---

**Happy hunting!** 🚀