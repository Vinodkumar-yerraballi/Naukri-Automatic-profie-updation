"""Export scored company-career workbook rows as reusable JSON."""

import json
from pathlib import Path

from openpyxl import load_workbook


WORKBOOK = Path("data/reports/company_careers_jobs.xlsx")
OUTPUT = Path("data/reports/company_careers_matches_over_70.json")
THRESHOLD = 70


def export_json(workbook_path=WORKBOOK, output_path=OUTPUT, threshold=THRESHOLD):
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    sheet = workbook["All Jobs"]
    headers = [cell.value for cell in next(sheet.iter_rows(max_row=1))]
    jobs = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, values))
        score = row.get("Match Score (%)")
        if score is None:
            continue
        jobs.append({
            "company": row.get("Company"),
            "title": row.get("Job Title"),
            "location": row.get("Location"),
            "experience": row.get("Experience"),
            "match_score_percent": score,
            "resume_skill_coverage_percent": row.get("Resume Skill Coverage (%)"),
            "matched_skills": [s.strip() for s in (row.get("Matching Skills") or "").split(",") if s.strip()],
            "missing_skills": [s.strip() for s in (row.get("Missing Skills") or "").split(",") if s.strip()],
            "resume_skills_evidenced": [s.strip() for s in (row.get("Resume Skills Evidenced") or "").split(",") if s.strip()],
            "description": row.get("Job Description"),
            "url": row.get("Job URL"),
        })
    errors_sheet = workbook["Scrape Errors"]
    error_headers = [cell.value for cell in next(errors_sheet.iter_rows(max_row=1))]
    errors = [dict(zip(error_headers, values)) for values in errors_sheet.iter_rows(min_row=2, values_only=True)]
    results = [job for job in jobs if job["match_score_percent"] > threshold]
    payload = {
        "threshold_percent_exclusive": threshold,
        "evaluated_job_count": len(jobs),
        "jobs_over_threshold_count": len(results),
        "scrape_error_count": len(errors),
        "source_files": [
            "C:/Users/vinod/Downloads/company_india_jobs.json",
            "C:/Users/vinod/Downloads/company_india_jobs_flat.json",
        ],
        "score_note": "Composite score uses config/profile.yaml and job preferences. Resume skill coverage is a separate skills-only comparison against data/resume.pdf.",
        "jobs_over_threshold": results,
        "scrape_errors": [
            {"company": e.get("Company"), "url": e.get("Job URL"), "error": e.get("Error")}
            for e in errors
        ],
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(results)} jobs above {threshold}% to {output_path} ({len(errors)} scrape errors recorded).")
    return output_path


if __name__ == "__main__":
    export_json()
