"""Export locally collected jobs to a recruiter-friendly Excel tracker.

The APPLY link opens the original job page. It does not submit an application.
For supported Naukri one-step applications, approve the job in the interactive
project review queue and verify the result on Naukri.

Each export creates two sheets:
- "Job Tracker": the job data with a Freshness column.
- "Log": a time-stamped log of this export run (rows found, date, etc.).
"""
from datetime import datetime
from pathlib import Path
import sqlite3

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# Original constants — test suite monkeypatches DB_PATH to a string path
DB_PATH = Path("data/job_automation.db")
OUTPUT_PATH = Path("data/reports/job_tracker.xlsx")

HEADERS = [
    "Job Title", "Company", "Platform", "Location", "Experience",
    "Freshness", "Match Score (%)", "Key Skills", "Job Status", "Date Found",
    "Job Link", "APPLY — OPEN JOB",
]
WIDTHS = [32, 24, 16, 26, 16, 14, 16, 48, 22, 22, 48, 24]


def freshness_label(posted: str, window_hours: int | None) -> str:
    """Render a short freshness label for the tracker cell."""
    if window_hours:
        return f"{window_hours}h window"
    if posted:
        return posted
    return "unknown"


def export_jobs(output_path: str | Path = OUTPUT_PATH) -> str:
    """Read the local jobs database and write an Excel review tracker.

    Accepts either a Path or a string path. Creates two sheets:
    - "Job Tracker": the job data with a Freshness column.
    - "Log": a time-stamped log of this export run (rows found, date, etc.).
    """
    db_path = output_path if isinstance(output_path, str) else Path(output_path)
    db = Path(DB_PATH)
    if not db.exists():
        raise FileNotFoundError(
            f"Jobs database not found: {db}. Run a job search first."
        )
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT title, company, source, location, experience,
                   posted, freshness_window_hours, match_score, skills,
                   status, date_found, job_url
            FROM jobs
            ORDER BY
                CASE WHEN match_score IS NULL THEN 1 ELSE 0 END,
                match_score DESC,
                id DESC
            """
        ).fetchall()
    finally:
        connection.close()

    # Date-stamped sheet names (Excel limit: 31 chars)
    today_label = datetime.now().strftime("%Y-%m-%d_%H-%M")
    tracker_sheet = "Job Tracker"
    log_sheet = f"Log_{today_label[:20]}"

    workbook = Workbook()
    # ---- Job Tracker sheet ----
    sheet = workbook.active
    sheet.title = tracker_sheet
    sheet.append(HEADERS)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{max(1, len(rows) + 1)}"
    sheet.row_dimensions[1].height = 34

    header_fill = PatternFill("solid", fgColor="17365D")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    for job in rows:
        score = job["match_score"]
        score_value = round(float(score), 2) if score is not None else None
        url = (job["job_url"] or "").strip()
        valid_url = url.startswith(("https://", "http://"))
        skills = job["skills"] or ""
        sheet.append([
            job["title"] or "",
            job["company"] or "",
            job["source"] or "",
            job["location"] or "",
            job["experience"] or "",
            freshness_label(job["posted"], job["freshness_window_hours"]),
            score_value,
            skills,
            job["status"] or "",
            job["date_found"] or "",
            url if valid_url else "",
            "OPEN JOB / APPLY" if valid_url else "LINK UNAVAILABLE",
        ])
        row_number = sheet.max_row
        # Column 6 (Freshness) centered
        sheet.cell(row_number, 6).alignment = Alignment(
            horizontal="center", vertical="center"
        )
        # Column 7 (Match Score) number format
        sheet.cell(row_number, 7).number_format = '0.00"%"'
        # Column 8 (Key Skills) wrapped, top-aligned
        sheet.cell(row_number, 8).alignment = Alignment(
            vertical="top", wrap_text=True
        )
        # Column 11 (Job Link) hyperlink
        if valid_url:
            apply_cell = sheet.cell(row_number, 11)
            apply_cell.hyperlink = url
            apply_cell.style = "Hyperlink"
            apply_cell.font = Font(
                color="FFFFFF", bold=True, underline="single"
            )
            apply_cell.fill = PatternFill("solid", fgColor="217346")
            apply_cell.alignment = Alignment(
                horizontal="center", vertical="center"
            )
        else:
            sheet.cell(row_number, 11).font = Font(
                color="808080", italic=True
            )
        # Column 12 (Apply link) hyperlink
        if valid_url:
            apply_cell_2 = sheet.cell(row_number, 12)
            apply_cell_2.hyperlink = url
            apply_cell_2.style = "Hyperlink"
            apply_cell_2.font = Font(
                color="FFFFFF", bold=True, underline="single"
            )
            apply_cell_2.fill = PatternFill("solid", fgColor="217346")
            apply_cell_2.alignment = Alignment(
                horizontal="center", vertical="center"
            )
        else:
            sheet.cell(row_number, 12).font = Font(
                color="808080", italic=True
            )
        sheet.row_dimensions[row_number].height = 32

    # Column widths
    for index, width in enumerate(WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    # Conditional formatting on Match Score column (G)
    if rows:
        sheet.conditional_formatting.add(
            f"G2:G{len(rows) + 1}",
            ColorScaleRule(
                start_type="num", start_value=0, start_color="F8696B",
                mid_type="num", mid_value=60, mid_color="FFEB84",
                end_type="num", end_value=100, end_color="63BE7B",
            ),
        )
        table = Table(
            displayName="JobTracker",
            ref=f"A1:{get_column_letter(len(HEADERS))}{len(rows) + 1}",
        )
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)

    # Comments
    sheet["F1"].comment = Comment(
        "This is the project's job-relevance match score, not an ATS score.",
        "Job Tracker",
    )
    sheet["K1"].comment = Comment(
        "Click to open the original job page. This link does not submit an "
        "application or bypass the project's individual approval step.",
        "Job Tracker",
    )

    # ---- Log sheet ----
    log_sheet = workbook.create_sheet(log_sheet)
    log_rows = [
        ["Export Log"],
        ["Export date/time:", datetime.now().astimezone().isoformat(timespec="seconds")],
        ["Total jobs in database:", str(len(rows))],
        ["Jobs exported:", str(len(rows))],
        ["Freshness window (project default):", "5 hours"],
        ["", ""],
        ["Job Source Distribution:"],
    ]
    # Count by source
    source_counts = {}
    for row in rows:
        src = row["source"] or "unknown"
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        log_rows.append([f"  {src}: {count} jobs"])
    log_rows += [
        ["", ""],
        ["Export generated:", datetime.now().astimezone().isoformat(timespec="seconds")],
    ]
    for row in log_rows:
        log_sheet.append(row)

    output_file = Path(output_path) if isinstance(output_path, str) else output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_file)
    print(f"Excel job tracker saved: {output_file}")
    print(f"Sheets: '{tracker_sheet}' (jobs), '{log_sheet}' (log)")
    print(f"Jobs exported: {len(rows)}")
    print("APPLY links open the job page; application approval remains in the CLI.")
    return str(output_file)


if __name__ == "__main__":
    export_jobs()