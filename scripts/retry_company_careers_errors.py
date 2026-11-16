"""Retry previously inaccessible company job URLs and refresh the workbook."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_manager import ConfigManager
from src.extraction.jd_extractor import JDExtractor
from src.ingestion.company_careers import CompanyCareersScraper
from src.matching.job_evaluator import JobEvaluator
from src.profile.profile_updater import ProfileManager
from scripts.company_careers_report import export_company_careers_report


WORKBOOK = Path("data/reports/company_careers_jobs.xlsx")
SEED = Path(r"C:\Users\vinod\Downloads\company_india_jobs_flat.json")


def _rows(sheet):
    values = list(sheet.values)
    return [dict(zip(values[0], row)) for row in values[1:]]


def retry_errors():
    seed_rows = json.loads(SEED.read_text(encoding="utf-8"))
    by_url = {str(row.get("url", "")).strip().lower(): row for row in seed_rows}
    workbook = load_workbook(WORKBOOK, data_only=True)
    old_jobs = _rows(workbook["All Jobs"])
    old_errors = _rows(workbook["Scrape Errors"])
    company_summaries = _rows(workbook["Company Summary"])
    jobs_by_url = {}
    for row in old_jobs:
        job = {
            "company": row.get("Company"), "title": row.get("Job Title"),
            "location": row.get("Location"), "experience": row.get("Experience"),
            "match_score": row.get("Match Score (%)"),
            "matching_skills": [x.strip() for x in (row.get("Matching Skills") or "").split(",") if x.strip()],
            "missing_skills": [x.strip() for x in (row.get("Missing Skills") or "").split(",") if x.strip()],
            "employment_type": row.get("Employment Type"), "posted": row.get("Date Posted"),
            "scraped_at": row.get("Date Found"), "description": row.get("Job Description"),
            "job_url": row.get("Job URL"),
        }
        jobs_by_url[str(job["job_url"]).lower()] = job

    retries_by_company = defaultdict(list)
    invalid_errors = []
    for error in old_errors:
        url = str(error.get("Job URL") or "").strip()
        record = by_url.get(url.lower())
        if record:
            retries_by_company[str(error.get("Company") or record.get("company"))].append(record)
        else:
            invalid_errors.append({"company": error.get("Company"), "job_url": url, "error": error.get("Error")})

    profile = ProfileManager("config/profile.yaml")
    profile.load_profile()
    prefs = ConfigManager().get_job_search_config()
    exp = prefs.get("experience", {})
    evaluator = JobEvaluator(
        candidate_skills=profile.get_all_skills(), target_roles=profile.get_target_roles(),
        preferred_locations=prefs.get("locations", []), preferred_work_modes=prefs.get("work_modes", []),
        candidate_min_experience=exp.get("minimum", 0), candidate_max_experience=exp.get("maximum", 2),
        candidate_education=profile.get_education(),
    )
    settings = json.loads(Path("config/company_careers.json").read_text(encoding="utf-8"))["settings"]
    threshold = float(settings.get("minimum_match_score", 70))
    scraped_at = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    retry_errors_out = []

    def run_company(company, records):
        scraper = CompanyCareersScraper(request_delay_seconds=settings.get("request_delay_seconds", 2), timeout_seconds=12)
        return company, *scraper.scrape_job_urls(company, records)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_company, company, records) for company, records in retries_by_company.items()]
        for future in as_completed(futures):
            company, scraped, pages, errors = future.result()
            for raw in scraped:
                parsed = JDExtractor(raw.get("description", "")).extract_all()
                job = {**parsed, **raw}
                job["skills"] = list(dict.fromkeys(parsed.get("skills", []) + raw.get("skills", [])))
                result = evaluator.evaluate(job)
                skill = result["skill_match"]
                job.update(match_score=result["final_score"], matching_skills=skill["matched_skills"], missing_skills=skill["missing_skills"], scraped_at=scraped_at)
                jobs_by_url[str(job["job_url"]).lower()] = job
            retry_errors_out.extend(errors)
            print(f"{company}: retry read {len(scraped)} descriptions; {len(errors)} still failed.")

    errors_by_url = {}
    for error in retry_errors_out:
        errors_by_url[str(error.get("job_url", "")).lower()] = error
    for error in invalid_errors:
        errors_by_url[str(error.get("job_url", "")).lower()] = error

    for summary in company_summaries:
        company = summary.get("Company")
        subset = [j for j in jobs_by_url.values() if j.get("company") == company]
        summary["Jobs Found"] = len(subset)
        summary["Jobs Above 70.0%"] = sum((j.get("match_score") or 0) > threshold for j in subset)
        unresolved = sum(e.get("company") == company for e in errors_by_url.values())
        summary["Status"] = "Complete" if not unresolved else ("Partial" if subset else "Failed")
        summary["Details"] = f"{unresolved} job URL(s) still unreadable; see Scrape Errors." if unresolved else ""

    export_company_careers_report(
        list(jobs_by_url.values()), company_summaries, minimum_score=threshold,
        output_path=WORKBOOK,
        job_errors=list(errors_by_url.values()),
    )
    print(f"Retry finished: {len(jobs_by_url)} readable jobs, {len(errors_by_url)} remaining errors.")


if __name__ == "__main__":
    retry_errors()
