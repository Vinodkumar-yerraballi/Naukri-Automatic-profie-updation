import json

from openpyxl import load_workbook

from scripts.company_careers_report import export_company_careers_report
from src.ingestion.company_careers import (
    CompanyCareersScraper,
    parse_career_page,
)


def test_parse_career_page_extracts_job_posting_and_job_links():
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Junior Data Analyst",
        "description": "<p>Use Python and SQL to analyze data.</p>",
        "url": "https://jobs.example.com/jobs/123",
        "hiringOrganization": {"@type": "Organization", "name": "Example"},
        "jobLocation": {
            "address": {
                "addressLocality": "Bengaluru",
                "addressCountry": "India",
            }
        },
        "skills": ["Python", "SQL"],
    }
    html = (
        '<script type="application/ld+json">'
        + json.dumps({"@graph": [posting]})
        + '</script><a href="/jobs/456">Another role</a>'
    )

    jobs, links = parse_career_page(
        html,
        "https://jobs.example.com/careers",
        "Example",
    )

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Junior Data Analyst"
    assert jobs[0]["company"] == "Example"
    assert jobs[0]["location"] == "Bengaluru, India"
    assert jobs[0]["skills"] == ["Python", "SQL"]
    assert "Python and SQL" in jobs[0]["description"]
    assert links == ["https://jobs.example.com/jobs/456"]


def test_scrape_job_urls_uses_source_title_and_reads_description(monkeypatch):
    scraper = CompanyCareersScraper(request_delay_seconds=0)
    html = (
        "<html><title>Company careers</title><body>"
        "<nav>Unrelated navigation words</nav>"
        "<main><h1>Details</h1><p>"
        + ("Use Python, SQL, and reporting tools to analyze data. " * 8)
        + "</p></main></body></html>"
    )
    monkeypatch.setattr(scraper, "_fetch", lambda _url: html)

    jobs, pages_read, errors = scraper.scrape_job_urls(
        "Example",
        [{
            "title": "Data Analyst",
            "location": "Bengaluru",
            "url": "https://jobs.example.com/jobs/123",
        }],
    )

    assert pages_read == 1
    assert errors == []
    assert jobs[0]["title"] == "Data Analyst"
    assert jobs[0]["location"] == "Bengaluru"
    assert "Unrelated navigation" not in jobs[0]["description"]
    assert "Python" in jobs[0]["description"]


def test_careers_report_keeps_equal_threshold_out_of_matched_sheet(tmp_path):
    output = tmp_path / "company_jobs.xlsx"
    jobs = [
        {
            "company": "Example",
            "title": "Data Analyst",
            "match_score": 70,
            "matching_skills": ["Python"],
            "missing_skills": ["Tableau"],
            "job_url": "https://jobs.example.com/jobs/70",
        },
        {
            "company": "Example",
            "title": "Senior Data Analyst",
            "match_score": 70.01,
            "matching_skills": ["Python", "SQL"],
            "missing_skills": [],
            "job_url": "https://jobs.example.com/jobs/71",
        },
    ]

    export_company_careers_report(
        jobs,
        [{"company": "Example", "status": "Complete"}],
        minimum_score=70,
        output_path=output,
    )

    workbook = load_workbook(output)
    assert workbook.sheetnames == [
        "Matched Jobs",
        "All Jobs",
        "Company Summary",
        "Skills Analysis",
        "Scrape Errors",
    ]
    assert workbook["Matched Jobs"].max_row == 2
    assert workbook["Matched Jobs"]["B2"].value == "Senior Data Analyst"
    assert (
        workbook["Matched Jobs"]["M2"].hyperlink.target
        == "https://jobs.example.com/jobs/71"
    )
    assert workbook["Matched Jobs"]["L2"].value == ""
    assert workbook["All Jobs"].max_row == 3
