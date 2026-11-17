"""Index India job URLs from the supplied grouped and flat JSON exports."""

import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from urllib.parse import urlsplit

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


FLAT = Path(r"C:\Users\vinod\Downloads\company_india_jobs_flat (1).json")
GROUPED = Path(r"C:\Users\vinod\Downloads\company_india_jobs (1).json")
OUTPUT_XLSX = Path("data/reports/company_opening_urls.xlsx")
OUTPUT_JSON = Path("data/reports/company_opening_urls.json")


def _write_table(ws, headers, rows, table_name):
    ws.append(headers)
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="17365D")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in rows:
        ws.append([json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for value in row])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for col in range(1, len(headers) + 1):
        width = max(15, min(56, max((len(str(ws.cell(r, col).value or "")) for r in range(1, ws.max_row + 1)), default=15) + 2))
        ws.column_dimensions[get_column_letter(col)].width = width
    if rows:
        table = Table(displayName=table_name, ref=f"A1:{get_column_letter(len(headers))}{len(rows)+1}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(table)


def run():
    flat = json.loads(FLAT.read_text(encoding="utf-8"))
    grouped = json.loads(GROUPED.read_text(encoding="utf-8"))
    grouped_jobs = [job for company in grouped.get("companies", []) for job in company.get("india_jobs", [])]
    grouped_urls = {str(job.get("url")).strip() for job in grouped_jobs if job.get("url")}
    flat_urls = {str(job.get("url")).strip() for job in flat if job.get("url")}
    source_agrees = grouped_urls == flat_urls

    by_url = defaultdict(list)
    for record in flat:
        url = str(record.get("url") or "").strip()
        if url:
            by_url[url].append(record)
    unique_rows = []
    for url, rows in sorted(by_url.items(), key=lambda item: (str(item[1][0].get("company", "")).casefold(), str(item[1][0].get("title", "")).casefold())):
        source = rows[0]
        parts = urlsplit(url)
        valid = parts.scheme in ("http", "https") and bool(parts.netloc) and "{" not in url and "}" not in url
        unique_rows.append({
            "company": source.get("company", ""), "title": source.get("title", ""),
            "location": source.get("location", ""), "job_id": source.get("job_id", ""),
            "jobs_listing_url": source.get("jobs_listing_url", ""), "job_url": url,
            "url_status": "Valid URL format" if valid else "Malformed placeholder URL",
            "source_record_count": len(rows),
        })

    companies = grouped.get("companies", [])
    company_rows = []
    for company in companies:
        positions = company.get("india_jobs") or []
        with_url = sum(bool(job.get("url")) for job in positions)
        company_rows.append([
            company.get("company", ""), company.get("rank", ""), company.get("status", ""),
            company.get("careers_url", ""), company.get("jobs_listing_url", ""),
            company.get("total_jobs_seen", ""), company.get("india_jobs_count", len(positions)),
            with_url, len(positions) - with_url, company.get("error", ""),
        ])

    missing = [r for r in flat if not r.get("url")]
    malformed = [r for r in unique_rows if r["url_status"] != "Valid URL format"]
    valid_count = len(unique_rows) - len(malformed)
    summary = {
        "source_files": [str(FLAT), str(GROUPED)],
        "generated_at": grouped.get("generated_at"),
        "country_filter": grouped.get("country_filter"),
        "flat_records": len(flat),
        "companies_in_grouped_file": len(companies),
        "companies_with_india_jobs": sum(bool(c.get("india_jobs")) for c in companies),
        "records_with_job_url": sum(bool(r.get("url")) for r in flat),
        "unique_job_urls": len(unique_rows),
        "valid_url_format_count": valid_count,
        "malformed_placeholder_url_count": len(malformed),
        "records_missing_url": len(missing),
        "grouped_and_flat_url_sets_match": source_agrees,
        "live_url_check": "Not performed; this export indexes and validates URL format only.",
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps({"summary": summary, "job_urls": unique_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    wb = Workbook()
    readme = wb.active
    readme.title = "Summary"
    _write_table(readme, ["Metric", "Value"], [[k, v] for k, v in summary.items()], "UrlSummary")
    urls_ws = wb.create_sheet("Unique Job URLs")
    _write_table(urls_ws, ["Company", "Job Title", "Location", "Job ID", "Company Listing URL", "Job URL", "URL Status", "Source Record Count"], [[r["company"], r["title"], r["location"], r["job_id"], r["jobs_listing_url"], r["job_url"], r["url_status"], r["source_record_count"]] for r in unique_rows], "UniqueJobUrls")
    for row_idx, row in enumerate(unique_rows, start=2):
        if row["url_status"] == "Valid URL format":
            urls_ws.cell(row_idx, 6).hyperlink = row["job_url"]
            urls_ws.cell(row_idx, 6).style = "Hyperlink"
    all_ws = wb.create_sheet("All Source Records")
    headers = ["Company", "Rank", "Title", "Location", "Job ID", "Company Listing URL", "Job URL", "URL Status"]
    rows = []
    for r in flat:
        url = str(r.get("url") or "").strip()
        part = urlsplit(url) if url else None
        status = "Missing URL" if not url else "Valid URL format" if part.scheme in ("http", "https") and part.netloc and "{" not in url and "}" not in url else "Malformed placeholder URL"
        rows.append([r.get("company", ""), r.get("rank", ""), r.get("title", ""), r.get("location", ""), r.get("job_id", ""), r.get("jobs_listing_url", ""), url, status])
    _write_table(all_ws, headers, rows, "AllSourceRecords")
    for idx, row in enumerate(rows, start=2):
        if row[-1] == "Valid URL format":
            all_ws.cell(idx, 7).hyperlink = row[6]
            all_ws.cell(idx, 7).style = "Hyperlink"
    company_ws = wb.create_sheet("Company Summary")
    _write_table(company_ws, ["Company", "Rank", "Source Status", "Careers URL", "Jobs Listing URL", "Total Jobs Seen", "India Jobs Count", "Records With URL", "Records Missing URL", "Error"], company_rows, "CompanySummary")
    wb.save(OUTPUT_XLSX)
    print(f"Saved {OUTPUT_XLSX} and {OUTPUT_JSON}: {len(unique_rows)} unique URLs; {valid_count} URL-format valid, {len(malformed)} malformed, {len(missing)} records without URLs. Sources agree: {source_agrees}.")


if __name__ == "__main__":
    run()
