"""Export locally collected jobs to a recruiter-friendly Excel tracker.

The APPLY link opens the original job page. It does not submit an application.
For supported Naukri one-step applications, approve the job in the interactive
project review queue and verify the result on Naukri.
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

DB_PATH = Path("data/job_automation.db")
OUTPUT_PATH = Path("data/reports/job_tracker.xlsx")

HEADERS = [
    "Job Title", "Company", "Platform", "Location", "Experience",
    "Match Score (%)", "Key Skills", "Job Status", "Date Found",
    "Job Link", "APPLY — OPEN JOB",
]
WIDTHS = [32, 24, 16, 26, 16, 16, 48, 22, 22, 48, 24]


def export_jobs(output_path: Path = OUTPUT_PATH) -> Path:
    """Read the local jobs database and write an Excel review tracker."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Jobs database not found: {DB_PATH}. Run a job search first."
        )

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT title, company, source, location, experience,
                   match_score, skills, status, date_found, job_url
            FROM jobs
            ORDER BY
                CASE WHEN match_score IS NULL THEN 1 ELSE 0 END,
                match_score DESC,
                id DESC
            """
        ).fetchall()
    finally:
        connection.close()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Job Tracker"
    sheet.append(HEADERS)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:K{max(1, len(rows) + 1)}"
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
            score_value,
            skills,
            job["status"] or "",
            job["date_found"] or "",
            url if valid_url else "",
            "OPEN JOB / APPLY" if valid_url else "LINK UNAVAILABLE",
        ])
        row_number = sheet.max_row
        sheet.cell(row_number, 6).number_format = '0.00"%"'
        sheet.cell(row_number, 7).alignment = Alignment(
            vertical="top", wrap_text=True
        )
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
        sheet.row_dimensions[row_number].height = 32

    for index, width in enumerate(WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    if rows:
        sheet.conditional_formatting.add(
            f"F2:F{len(rows) + 1}",
            ColorScaleRule(
                start_type="num", start_value=0, start_color="F8696B",
                mid_type="num", mid_value=60, mid_color="FFEB84",
                end_type="num", end_value=100, end_color="63BE7B",
            ),
        )
        table = Table(
            displayName="JobTracker",
            ref=f"A1:K{len(rows) + 1}",
        )
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)

    sheet["F1"].comment = Comment(
        "This is the project's job-relevance match score, not an ATS score.",
        "Job Tracker",
    )
    sheet["K1"].comment = Comment(
        "Click to open the original job page. This link does not submit an "
        "application or bypass the project's individual approval step.",
        "Job Tracker",
    )

    guide = workbook.create_sheet("Read Me")
    guide_rows = [
        ["HOW TO USE THIS JOB TRACKER"],
        ["1. Run a search in PowerShell from the project folder:"],
        [r".venv\Scripts\python.exe main.py --search-naukri"],
        [r".venv\Scripts\python.exe main.py --search-instahyre"],
        [r".venv\Scripts\python.exe main.py --search-shine"],
        ["2. Export the latest local job database:"],
        [r".venv\Scripts\python.exe main.py --export-jobs-excel"],
        ["3. Open the Job Tracker sheet and compare score, skills, location, and experience."],
        ["4. Click the green OPEN JOB / APPLY link to open the original listing."],
        ["5. For a supported Naukri application, return to PowerShell and run:"],
        [r".venv\Scripts\python.exe main.py"],
        ["6. Review the job and resume, then type A only when you approve that job."],
        ["R = reject | S = skip | Q = quit"],
        ["The Excel link opens the listing only. It does not submit an application."],
        ["The match score is the project's relevance score, not an ATS score."],
        ["The workbook is an export. Editing cells here does not update the app database."],
        [f"Export generated: {datetime.now().astimezone().isoformat(timespec='seconds')}"],
    ]
    for row in guide_rows:
        guide.append(row)
    guide.merge_cells("A1:D1")
    guide["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    guide["A1"].fill = header_fill
    guide["A1"].alignment = Alignment(vertical="center")
    guide.row_dimensions[1].height = 30
    guide.column_dimensions["A"].width = 105
    for row in guide.iter_rows(min_row=2):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
        if row[0].value and str(row[0].value).startswith(".venv"):
            row[0].font = Font(name="Consolas", color="1F4E78")
    guide.freeze_panes = "A2"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    print(f"Excel job tracker saved: {output_path}")
    print(f"Jobs exported: {len(rows)}")
    print("APPLY links open the job page; application approval remains in the CLI.")
    return output_path


if __name__ == "__main__":
    export_jobs()
