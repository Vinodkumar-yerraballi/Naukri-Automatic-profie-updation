"""Crawl unique company careers portals and export discovered openings."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
import re
import sys
import json
from urllib.parse import urlsplit, urlunsplit

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.config_manager import ConfigManager
from src.ingestion.company_careers import CompanyCareersScraper
from src.matching.job_evaluator import JobEvaluator
from src.profile.profile_updater import ProfileManager

INPUT = Path(r"C:\Users\vinod\Downloads\200 - Career Portal Links.xlsx")
OUTPUT = Path("data/reports/company_portal_openings.xlsx")
CHECKPOINT = Path("data/reports/company_portal_crawl_checkpoint.json")
FRESH_DAYS = 30
MAX_PAGES = 25
MAX_JOBS = 300
DELAY_SECONDS = 2


def normalize_url(value):
    parts = urlsplit(str(value or "").strip())
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, ""))


def freshness(value):
    if not value:
        return "Unknown"
    text = str(value).lower()
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        try:
            age = (date.today() - date.fromisoformat(match.group())).days
            return "Fresh" if 0 <= age <= FRESH_DAYS else "Older"
        except ValueError:
            pass
    match = re.search(r"(\d+)\s*(hour|day|week|month)", text)
    if match:
        count, unit = int(match.group(1)), match.group(2)
        days = count / 24 if unit == "hour" else count if unit == "day" else count * 7 if unit == "week" else count * 30
        return "Fresh" if days <= FRESH_DAYS else "Older"
    return "Fresh" if text.strip() in {"today", "just posted", "new"} else "Unknown"


INDIA_TERMS = ("india", "bengaluru", "bangalore", "hyderabad", "chennai", "mumbai", "pune", "gurugram", "gurgaon", "new delhi", "noida", "kolkata", "ahmedabad", "jaipur", "kochi", "kerala", "karnataka", "telangana", "tamil nadu", "maharashtra", "gujarat", "uttar pradesh", "andhra pradesh")
FOREIGN_TERMS = ("united states", "usa", "u.s.", "canada", "united kingdom", "uk", "germany", "france", "australia", "singapore", "japan", "netherlands")


def region_scope(location):
    text = str(location or "").lower()
    if not text:
        return "Unknown"
    if re.search(r"\bindia\b", text) or any(term in text for term in INDIA_TERMS[1:]) or re.search(r"(^|[,\s])in([,\s]|$)", text):
        return "India"
    if any(term in text for term in FOREIGN_TERMS):
        return "Outside India"
    return "Unknown"


def write_sheet(ws, headers, rows, table_name):
    ws.append(headers)
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in rows:
        ws.append([ILLEGAL_CHARACTERS_RE.sub("", str(value)) if isinstance(value, str) else value for value in row])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[ws.max_row].height = 36
    for col in range(1, len(headers) + 1):
        width = min(50, max(16, max((len(str(ws.cell(r, col).value or "")) for r in range(1, ws.max_row + 1)), default=16) + 2))
        ws.column_dimensions[get_column_letter(col)].width = width
    if rows:
        table = Table(displayName=table_name, ref=f"A1:{get_column_letter(len(headers))}{len(rows)+1}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(table)


def run():
    rows = list(load_workbook(INPUT, read_only=True, data_only=True).active.values)
    portals = {}
    for row_number, row in enumerate(rows[1:], start=2):
        category, company, careers_url = (list(row) + [None] * 3)[:3]
        key = normalize_url(careers_url)
        if not key:
            continue
        portal = portals.setdefault(key, {"url": key, "companies": [], "categories": [], "source_rows": []})
        if company and str(company).strip() not in portal["companies"]:
            portal["companies"].append(str(company).strip())
        if category and str(category).strip() not in portal["categories"]:
            portal["categories"].append(str(category).strip())
        portal["source_rows"].append(row_number)

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

    def crawl(portal):
        company = portal["companies"][0] if portal["companies"] else urlsplit(portal["url"]).netloc
        scraper = CompanyCareersScraper(request_delay_seconds=DELAY_SECONDS, max_pages_per_company=MAX_PAGES, max_jobs_per_company=MAX_JOBS, timeout_seconds=15)
        try:
            jobs, pages = scraper.scrape_company(company, portal["url"])
            return portal, jobs, pages, "Complete" if jobs else "No jobs extracted", ""
        except Exception as error:
            return portal, [], 0, "Failed", f"{type(error).__name__}: {error}"

    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    try:
        checkpoint_data = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        checkpoint_data = {}
    completed = checkpoint_data.get("portals", {})
    jobs_all = [job for item in completed.values() for job in item["jobs_data"]]
    portal_results = [item["portal_result"] for item in completed.values()]
    for job in jobs_all:
        job["region_scope"] = region_scope(job.get("location"))
    for portal_result in portal_results:
        portal_jobs = [job for job in jobs_all if job.get("source_portal") == portal_result["url"]]
        portal_result["india_jobs"] = sum(job.get("region_scope") == "India" for job in portal_jobs)
        portal_result["fresh_india"] = sum(job.get("region_scope") == "India" and job.get("freshness_status") == "Fresh" for job in portal_jobs)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(crawl, p) for key, p in portals.items() if key not in completed]
        for future in as_completed(futures):
            portal, jobs, pages, status, error = future.result()
            scored_jobs = []
            for job in jobs:
                result = evaluator.evaluate(job)
                job["score"] = result["final_score"]
                job["score_category"] = result["score_category"]
                job["matching_skills"] = result["skill_match"]["matched_skills"]
                job["missing_skills"] = result["skill_match"]["missing_skills"]
                job["freshness_status"] = freshness(job.get("posted"))
                job["region_scope"] = region_scope(job.get("location"))
                job["source_portal"] = portal["url"]
                jobs_all.append(job)
                scored_jobs.append(job)
            fresh_count = sum(freshness(job.get("posted")) == "Fresh" for job in jobs)
            portal_result = {**portal, "pages": pages, "jobs": len(jobs), "fresh": fresh_count, "india_jobs": sum(region_scope(j.get("location")) == "India" for j in jobs), "fresh_india": sum(region_scope(j.get("location")) == "India" and freshness(j.get("posted")) == "Fresh" for j in jobs), "status": status, "error": error}
            portal_results.append(portal_result)
            completed[portal["url"]] = {"portal_result": portal_result, "jobs_data": scored_jobs}
            CHECKPOINT.write_text(json.dumps({"portals": completed}, ensure_ascii=False, default=str), encoding="utf-8")
            print(f"{', '.join(portal['companies'][:2])}: {len(jobs)} listings, {fresh_count} fresh, {status}", flush=True)

    seen, unique_jobs = set(), []
    for job in jobs_all:
        url = str(job.get("job_url", "")).strip().lower()
        if url and url not in seen:
            seen.add(url)
            unique_jobs.append(job)
    unique_jobs.sort(key=lambda job: job.get("score", 0), reverse=True)
    qualified = [job for job in unique_jobs if job.get("score", 0) > 70 and job.get("region_scope") == "India"]
    india_jobs = [job for job in unique_jobs if job.get("region_scope") == "India"]

    def job_row(job):
        return [job.get("company", ""), job.get("title", ""), job.get("location", ""), job.get("region_scope", "Unknown"), job.get("experience", ""), job.get("posted", ""), job.get("freshness_status", "Unknown"), job.get("score"), job.get("score_category", ""), ", ".join(job.get("matching_skills", [])), ", ".join(job.get("missing_skills", [])), str(job.get("description", ""))[:32767], job.get("job_url", ""), ""]

    wb = Workbook()
    summary = wb.active
    summary.title = "Portal Summary"
    summary_rows = [[", ".join(p["companies"]), ", ".join(p["categories"]), p["url"], len(p["source_rows"]), p["pages"], p["jobs"], p.get("india_jobs", 0), p.get("fresh_india", 0), p["fresh"], p["status"], p["error"]] for p in sorted(portal_results, key=lambda p: p["companies"][0].lower() if p["companies"] else p["url"])]
    write_sheet(summary, ["Company", "Category", "Career Portal URL", "Source Rows", "Pages Visited", "Open Listings Found", "India Listings", "Fresh India (<=30 days)", "Fresh Overall (<=30 days)", "Status", "Error"], summary_rows, "PortalSummary")
    headers = ["Company", "Job Title", "Location", "Region Scope", "Experience", "Date Posted", "Freshness (<=30 days)", "Match Score (%)", "Score Category", "Matched Skills", "Missing Skills", "Job Description", "Job URL", "Apply / View"]
    for title, jobs, table_name in [("Over 70% India", qualified, "JobsOver70India"), ("India Openings", india_jobs, "IndiaPortalOpenings"), ("All Listings", unique_jobs, "AllPortalListings")]:
        ws = wb.create_sheet(title)
        write_sheet(ws, headers, [job_row(job) for job in jobs], table_name)
        for index, job in enumerate(jobs, start=2):
            ws.cell(index, 8).number_format = '0.00"%"'
            url = job.get("job_url", "")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                ws.cell(index, 14).value = "APPLY / VIEW"
                ws.cell(index, 14).hyperlink = url
                ws.cell(index, 14).style = "Hyperlink"
    duplicate_ws = wb.create_sheet("Duplicate Portals")
    duplicate_rows = [[p["url"], ", ".join(p["companies"]), ", ".join(p["categories"]), ", ".join(map(str, p["source_rows"])), "Crawled once"] for p in portal_results if len(p["source_rows"]) > 1]
    write_sheet(duplicate_ws, ["Career Portal URL", "Companies", "Categories", "Workbook Rows", "Handling"], duplicate_rows, "DuplicatePortals")
    notes = wb.create_sheet("Read Me")
    note_rows = [["Metric", "Definition"], ["Portals", f"{len(portals)} unique normalized career URLs from {len(rows)-1} workbook rows; duplicate portals were crawled once."], ["Open listings", f"Jobs extracted from accessible pages, capped at {MAX_PAGES} pages and {MAX_JOBS} jobs per portal. Counts reflect discovered listings, not guaranteed full employer inventory."], ["Fresh", f"Posting date within {FRESH_DAYS} days of the crawl date. Undated listings are Unknown."], ["India scope", "India Openings requires an India country code/name or recognized Indian city/state in the published location. Missing or ambiguous locations stay in All Listings as Unknown."], ["Match score", "Candidate-specific score using config/profile.yaml and config/job_preferences.yaml. Over 70% India includes scores strictly greater than 70."], ["Apply / View", "Clickable link opens the employer's job page. Application is completed on the employer site."]]
    for row in note_rows:
        notes.append(row)
    for cell in notes[1]:
        cell.fill = PatternFill("solid", fgColor="17365D"); cell.font = Font(color="FFFFFF", bold=True)
    notes.column_dimensions["A"].width = 25; notes.column_dimensions["B"].width = 115
    for row in notes.iter_rows():
        for cell in row: cell.alignment = Alignment(wrap_text=True, vertical="top")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT)
    print(f"Saved {OUTPUT}: {len(portals)} unique portals, {len(unique_jobs)} unique listings, {len(qualified)} above 70%.", flush=True)


if __name__ == "__main__":
    run()
