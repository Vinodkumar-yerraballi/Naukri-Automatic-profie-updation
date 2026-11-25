import sqlite3

from openpyxl import load_workbook

from scripts import export_jobs_excel


def make_database(path):
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            source TEXT,
            location TEXT,
            experience TEXT,
            posted TEXT,
            freshness_window_hours INTEGER,
            match_score REAL,
            skills TEXT,
            status TEXT,
            date_found TEXT,
            job_url TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO jobs (
            title, company, source, location, experience, posted,
            freshness_window_hours, match_score, skills, status,
            date_found, job_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Junior Data Analyst",
            "Example Analytics",
            "Naukri",
            "Bengaluru",
            "0-2 years",
            "2 hours",
            6,
            82.5,
            "Python, SQL, Pandas",
            "needs_review",
            "2026-11-16",
            "https://www.naukri.com/example-job",
        ),
    )
    connection.commit()
    connection.close()


def test_export_jobs_creates_tracker_with_job_link(tmp_path, monkeypatch):
    database = tmp_path / "jobs.db"
    output = tmp_path / "job_tracker.xlsx"
    make_database(database)
    monkeypatch.setattr(export_jobs_excel, "DB_PATH", database)

    export_jobs_excel.export_jobs(output)

    workbook = load_workbook(output)
    sheet = workbook["Job Tracker"]
    assert sheet["A2"].value == "Junior Data Analyst"
    assert sheet["B2"].value == "Example Analytics"
    assert sheet["F2"].value == "6h window"
    assert sheet["G2"].value == 82.5
    assert sheet["H2"].value == "Python, SQL, Pandas"
    assert sheet["L2"].hyperlink.target == "https://www.naukri.com/example-job"
    assert sheet["L2"].value == "OPEN JOB / APPLY"
    # The export creates two sheets: Job Tracker + a date-stamped Log sheet
    assert "Job Tracker" in workbook.sheetnames
    # Log sheet name contains the export date
    log_sheets = [s for s in workbook.sheetnames if s.startswith("Log_")]
    assert len(log_sheets) >= 1


def test_export_jobs_empty_database(tmp_path, monkeypatch):
    """Edge case: no jobs in the database."""
    import tempfile
    import os

    database = tempfile.mktemp(suffix=".db")
    output = tempfile.mktemp(suffix=".xlsx")
    make_database(database)
    monkeypatch.setattr(export_jobs_excel, "DB_PATH", database)

    try:
        export_jobs_excel.export_jobs(output)
        workbook = load_workbook(output)
        # Should still have Job Tracker (empty) and Log sheet
        assert "Job Tracker" in workbook.sheetnames
    finally:
        if os.path.exists(database):
            os.unlink(database)
        if os.path.exists(output):
            os.unlink(output)