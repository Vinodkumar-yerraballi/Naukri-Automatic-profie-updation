import csv
import json

import pytest

from scripts import daily_job_report as report


def test_select_search_queries_is_bounded_and_unique():
    queries = report.select_search_queries(
        ["Data Analyst", "Data Scientist"],
        ["Remote", "Bangalore"],
        3,
    )

    assert len(queries) == 3
    assert len(queries) == len(set(queries))
    assert {role for role, _ in queries} == {"Data Analyst", "Data Scientist"}
    assert {location for _, location in queries}.issubset({"Remote", "Bangalore"})


def test_only_fresh_role_matched_jobs_above_threshold_are_eligible():
    base = {
        "fresh": True,
        "role_match": True,
        "description_available": True,
        "match_score": 85,
    }
    assert report.is_review_eligible(base, 85)
    assert not report.is_review_eligible({**base, "fresh": False}, 85)
    assert not report.is_review_eligible({**base, "role_match": False}, 85)
    assert not report.is_review_eligible({**base, "description_available": False}, 85)
    assert not report.is_review_eligible({**base, "match_score": 84.99}, 85)


def test_write_reports_creates_markdown_csv_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "REPORT_DIR", tmp_path)
    rows = [{
        "run_at_ist": "2026-10-27T09:00:00+05:30",
        "title": "Data Analyst",
        "company": "Example Co",
        "location": "Remote",
        "experience": "0-2 years",
        "posted": "5 hours ago",
        "match_score": 90,
        "fresh": True,
        "role_match": True,
        "eligible_for_review": True,
        "matched_role": "data analyst",
        "matched_skills": "Python, SQL",
        "job_url": "https://www.naukri.com/example-job",
        "description_available": True,
        "notes": "",
    }]

    markdown_path, csv_path, summary_path = report.write_reports(
        rows,
        report.datetime(2026, 10, 27, 9, 0, tzinfo=report.IST),
        "SUCCESS",
    )

    assert "Eligible for review" in markdown_path.read_text(encoding="utf-8")
    assert "application submission: disabled" in markdown_path.read_text(encoding="utf-8").lower()
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 1
    assert csv_rows[0]["title"] == "Data Analyst"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["eligible_for_review"] == 1
    assert summary["application_submission_enabled"] is False


def test_access_denied_report_is_recorded_and_fails(tmp_path, monkeypatch):
    class FakeBrowser:
        def __init__(self, headless):
            pass

        def start_persistent(self, user_data_dir):
            # Match the persistent-session API used by run_report().
            pass

        def search_jobs(self, **kwargs):
            pass

        def detect_access_denied(self):
            return True

        def detect_security_challenge(self):
            raise AssertionError("Should stop when access is denied.")

        def close(self):
            pass

    monkeypatch.setattr(report, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(report, "NaukriBrowser", FakeBrowser)
    with pytest.raises(SystemExit, match="Naukri denied access"):
        report.run_report()

    markdown_path = next(tmp_path.glob("*.md"))
    summary_path = next(tmp_path.glob("*.json"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "ACCESS_DENIED"
    assert summary["fresh_jobs_evaluated"] == 0
    assert "denied access" in summary["message"]
    assert "Status: ACCESS_DENIED" in markdown_path.read_text(encoding="utf-8")
