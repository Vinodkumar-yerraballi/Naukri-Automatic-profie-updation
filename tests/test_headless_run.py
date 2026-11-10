import sys

import main
import scripts.daily_job_report as daily_job_report


class _ConfigManager:
    def get_naukri_profile_config(self):
        return {}

    def get_resume_tailoring_config(self):
        return {}

    def get_resume_platform_configs(self):
        return {}

    def get_job_search_config(self):
        return {
            "roles": ["Data Analyst"],
            "locations": ["Remote"],
            "max_searches_per_run": 1,
        }

    def get_minimum_score(self):
        return 75


class _Browser:
    def __init__(self, headless):
        self.headless = headless
        self.playwright = object()

    def start(self):
        pass

    def search_jobs(self, **kwargs):
        pass

    def detect_access_denied(self):
        return False

    def detect_security_challenge(self):
        return False

    def get_job_cards(self):
        return []

    def close(self):
        pass


class _ProfileManager:
    def __init__(self, profile_path):
        pass

    def load_profile(self):
        pass

    def get_all_skills(self):
        return []

    def get_target_roles(self):
        return ["Data Analyst"]

    def get_education(self):
        return []


class _Repository:
    def __init__(self):
        self.jobs = [
            {
                "title": "Data Analyst",
                "company": "Example Co",
                "location": "Remote",
                "match_score": 88,
                "status": "REVIEW",
                "source": "Naukri",
                "job_url": "https://example.test/job",
            }
        ]

    def get_review_jobs(self):
        return self.jobs

    def update_status(self, job_url, status):
        for job in self.jobs:
            if job["job_url"] == job_url:
                job["status"] = status


class _FailingStdin:
    def read(self, *args, **kwargs):
        return _raise_on_stdin_read(*args, **kwargs)

    def readline(self, *args, **kwargs):
        return _raise_on_stdin_read(*args, **kwargs)


def _raise_on_stdin_read(*args, **kwargs):
    raise AssertionError("Headless run attempted to read from stdin.")


def test_headless_run_never_reads_stdin(monkeypatch, tmp_path):
    browser_instances = []
    repository = _Repository()

    def create_browser(headless):
        browser = _Browser(headless)
        browser_instances.append(browser)
        return browser

    monkeypatch.setattr(main, "ConfigManager", _ConfigManager)
    monkeypatch.setattr(main, "NaukriBrowser", create_browser)
    monkeypatch.setattr(main, "ProfileManager", _ProfileManager)
    monkeypatch.setattr(main, "JobRepository", lambda: repository)
    monkeypatch.setattr(
        daily_job_report, "REPORT_DIR", tmp_path / "reports"
    )
    monkeypatch.setattr("builtins.input", _raise_on_stdin_read)
    monkeypatch.setattr(sys, "stdin", _FailingStdin())

    main.main(run_review=False, headless=True)

    assert browser_instances[0].headless is True
    assert repository.jobs[0]["status"] == "needs_review"
    assert list((tmp_path / "reports").glob("headless_review_queue_*.md"))


def test_headless_review_report_includes_score_and_needs_review_status(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(daily_job_report, "REPORT_DIR", tmp_path)

    paths = daily_job_report.write_headless_review_report(
        [
            {
                "title": "Data Analyst",
                "company": "Example Co",
                "location": "Remote",
                "match_score": 88,
                "status": "REVIEW",
                "source": "Naukri",
                "job_url": "https://example.test/job",
            }
        ],
        run_time=daily_job_report.datetime(
            2026, 11, 10, 9, 0, tzinfo=daily_job_report.IST
        ),
    )

    content = paths["markdown"].read_text(encoding="utf-8")
    assert "Match score: 88" in content
    assert "Status: needs_review" in content


def test_needs_review_status_remains_in_database_review_queue(tmp_path):
    repository = main.JobRepository(str(tmp_path / "jobs.db"))
    job = {
        "title": "Data Analyst",
        "company": "Example Co",
        "location": "Remote",
        "experience": "0-2 years",
        "job_url": "https://example.test/job",
        "description": "Analyze business data.",
        "skills": ["Python", "SQL"],
        "match_score": 88,
        "status": "needs_review",
        "source": "Naukri",
    }

    assert repository.add_job(job)
    queued_jobs = repository.get_review_jobs()

    assert len(queued_jobs) == 1
    assert queued_jobs[0]["match_score"] == 88
    assert queued_jobs[0]["status"] == "needs_review"
