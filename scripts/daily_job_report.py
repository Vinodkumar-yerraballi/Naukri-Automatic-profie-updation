"""Generate a fresh-job review report without submitting applications."""
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config.config_manager import ConfigManager
from src.extraction.jd_extractor import JDExtractor
from src.ingestion.naukri_browser import NaukriBrowser
from src.matching.freshness_matcher import FreshnessMatcher
from src.matching.job_evaluator import JobEvaluator
from src.profile.profile_updater import ProfileManager


IST = ZoneInfo("Asia/Kolkata")
REPORT_DIR = Path("data/reports")
MAX_DETAIL_PAGES = 20
CSV_FIELDS = [
    "run_at_ist", "title", "company", "location", "experience", "posted",
    "match_score", "eligible_for_review", "matched_role", "matched_skills",
    "job_url", "description_available", "notes",
]


def select_search_queries(roles, locations, max_searches):
    """Build a bounded, deterministic list of role/location searches."""
    if not roles or not locations or max_searches < 1:
        return []
    queries = []
    for location in locations:
        for role in roles:
            item = (role, location)
            if item not in queries:
                queries.append(item)
            if len(queries) >= max_searches:
                return queries
    return queries


def is_review_eligible(job, minimum_score):
    """Only fresh, role-matched jobs above the configured score qualify."""
    return (
        job.get("fresh") is True
        and job.get("role_match") is True
        and job.get("description_available") is True
        and isinstance(job.get("match_score"), (int, float))
        and job["match_score"] >= minimum_score
    )


def write_reports(rows, run_time, run_status, message=""):
    """Write Markdown and CSV reports for GitHub Actions artifact upload."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = run_time.strftime("%Y-%m-%d_%H-%M-%S")
    csv_path = REPORT_DIR / f"daily_jobs_{stamp}_IST.csv"
    md_path = REPORT_DIR / f"daily_jobs_{stamp}_IST.md"
    summary_path = REPORT_DIR / f"daily_jobs_{stamp}_IST.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})

    eligible = [row for row in rows if row.get("eligible_for_review")]
    lines = [
        "# Daily Naukri Job Review Report",
        "",
        f"- Run time: {run_time.isoformat()}",
        f"- Status: {run_status}",
        f"- Fresh jobs evaluated: {len(rows)}",
        f"- Eligible for manual review: {len(eligible)}",
        "- Application submission: DISABLED — review only",
    ]
    if message:
        lines.extend(["", f"- Note: {message}"])

    for heading, selected in (
        ("Eligible for review", eligible),
        ("Other fresh jobs", [row for row in rows if not row.get("eligible_for_review")]),
    ):
        lines.extend(["", f"## {heading}", ""])
        if not selected:
            lines.append("No jobs in this section.")
            continue
        for row in selected:
            lines.extend([
                f"### {row.get('title') or 'Untitled job'} — {row.get('company') or 'Company not listed'}",
                f"- Match score: {row.get('match_score', 'N/A')}",
                f"- Location: {row.get('location') or 'Not listed'}",
                f"- Experience: {row.get('experience') or 'Not listed'}",
                f"- Posted: {row.get('posted') or 'Unknown'}",
                f"- Matched role: {row.get('matched_role') or 'No direct role match'}",
                f"- Matched skills: {row.get('matched_skills') or 'Not identified'}",
                f"- URL: {row.get('job_url') or 'Unavailable'}",
                "",
            ])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_path.write_text(
        json.dumps({
            "run_at_ist": run_time.isoformat(),
            "status": run_status,
            "message": message,
            "fresh_jobs_evaluated": len(rows),
            "eligible_for_review": len(eligible),
            "application_submission_enabled": False,
            "markdown_report": str(md_path),
            "csv_report": str(csv_path),
        }, indent=2),
        encoding="utf-8",
    )
    return md_path, csv_path, summary_path


def run_report():
    run_time = datetime.now(IST)
    rows = []
    status = "SUCCESS"
    message = ""
    browser = None

    try:
        config = ConfigManager()
        search = config.get_job_search_config()
        profile = ProfileManager("config/profile.yaml")
        profile.load_profile()
        experience = search.get("experience", {})
        freshness_limit = int(search.get("posted_within_hours", 24))
        minimum_score = config.get_minimum_score()

        evaluator = JobEvaluator(
            candidate_skills=profile.get_all_skills(),
            target_roles=profile.get_target_roles(),
            preferred_locations=search.get("locations", []),
            preferred_work_modes=search.get("work_modes", []),
            candidate_min_experience=int(experience.get("minimum", 0)),
            candidate_max_experience=int(experience.get("maximum", 2)),
            candidate_education=profile.get_education(),
        )
        freshness = FreshnessMatcher()
        queries = select_search_queries(
            search.get("roles", []),
            search.get("locations", []),
            max(1, int(search.get("max_searches_per_run", 8))),
        )

        browser = NaukriBrowser(headless=True)
        browser.start()
        cards_by_url = {}

        for role, location in queries:
            browser.search_jobs(
                role=role,
                location=location,
                posted_within_hours=freshness_limit,
                experience=experience,
            )
            if browser.detect_security_challenge():
                status = "MANUAL_ACTION_REQUIRED"
                message = (
                    "Naukri displayed a security challenge during search. "
                    "The run stopped without attempting to solve it."
                )
                break
            for card in browser.get_job_cards():
                if not freshness.is_within_last_hours(
                    card.get("posted", ""),
                    max_hours=freshness_limit,
                ):
                    continue
                url = card.get("job_url", "").strip()
                if url.startswith("https://www.naukri.com/"):
                    cards_by_url.setdefault(url, card)

        if status == "SUCCESS":
            cards = list(cards_by_url.values())[:MAX_DETAIL_PAGES]
            for card in cards:
                details = browser.extract_job_details(dict(card))
                if details.get("security_challenge"):
                    status = "MANUAL_ACTION_REQUIRED"
                    message = (
                        "Naukri displayed a security challenge while opening "
                        "a job. The report contains only jobs processed so far."
                    )
                    break

                description = details.get("job_description", "") or ""
                extracted = JDExtractor(description).extract_all() if description else {}
                evaluated_job = {
                    **extracted,
                    **details,
                    "title": details.get("title") or extracted.get("title", ""),
                    "company": details.get("company", ""),
                    "location": details.get("location") or extracted.get("location", ""),
                    "experience": details.get("experience") or extracted.get("experience", ""),
                    "posted": details.get("posted", ""),
                    "education": details.get("education", []),
                    "skills": extracted.get("skills", []),
                }
                evaluation = evaluator.evaluate(evaluated_job)
                role_result = evaluation.get("role_match", {})
                skill_result = evaluation.get("skill_match", {})
                score = evaluation.get("final_score")
                fresh = freshness.is_within_last_hours(
                    details.get("posted", ""),
                    max_hours=freshness_limit,
                )
                row = {
                    "run_at_ist": run_time.isoformat(),
                    "title": evaluated_job.get("title", ""),
                    "company": evaluated_job.get("company", ""),
                    "location": evaluated_job.get("location", ""),
                    "experience": evaluated_job.get("experience", ""),
                    "posted": details.get("posted", ""),
                    "match_score": score,
                    "fresh": fresh,
                    "role_match": bool(role_result.get("match")),
                    "eligible_for_review": False,
                    "matched_role": role_result.get("matched_role") or "",
                    "matched_skills": ", ".join(skill_result.get("matched_skills", []) or []),
                    "job_url": details.get("job_url", ""),
                    "description_available": bool(description),
                    "notes": "",
                }
                if not description:
                    row["notes"] = "Job description unavailable; score may be less informative."
                row["eligible_for_review"] = is_review_eligible(row, minimum_score)
                rows.append(row)

    except Exception as error:
        status = "ERROR"
        message = f"{type(error).__name__}: {error}"
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    reports = write_reports(rows, run_time, status, message)
    for report_path in reports:
        print(f"REPORT: {report_path}")
    print(f"REPORT_STATUS: {status}")
    print(f"FRESH_JOBS: {len(rows)}")
    print(f"ELIGIBLE_FOR_REVIEW: {sum(bool(row.get('eligible_for_review')) for row in rows)}")
    if message:
        print(f"REPORT_MESSAGE: {message}")
    if status == "ERROR":
        raise RuntimeError(message)
    return reports


if __name__ == "__main__":
    run_report()
