"""Export company-career findings to a separate Excel workbook."""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


DEFAULT_OUTPUT_PATH = Path("data/reports/company_careers_jobs.xlsx")
JOB_HEADERS = [
    "Company",
    "Job Title",
    "Location",
    "Experience",
    "Match Score (%)",
    "Matching Skills",
    "Missing Skills",
    "Employment Type",
    "Date Posted",
    "Date Found",
    "Job Description",
    "Job URL",
    "Open Job",
]


def _format_sheet(sheet, headers, rows, table_name=None):
    sheet.append(headers)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(rows) + 1)}"
    sheet.row_dimensions[1].height = 32

    header_fill = PatternFill("solid", fgColor="17365D")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    for row in rows:
        sheet.append(row)
        row_number = sheet.max_row
        for cell in sheet[row_number]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        if "Match Score (%)" in headers:
            score_cell = sheet.cell(
                row_number, headers.index("Match Score (%)") + 1
            )
            score_cell.number_format = '0.00"%"'
        if "Job URL" in headers and "Open Job" in headers:
            url_index = headers.index("Job URL") + 1
            link_index = headers.index("Open Job") + 1
            url = sheet.cell(row_number, url_index).value
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                link_cell = sheet.cell(row_number, link_index)
                link_cell.hyperlink = url
                link_cell.value = "OPEN JOB"
                link_cell.style = "Hyperlink"
        sheet.row_dimensions[row_number].height = 32

    for index in range(1, len(headers) + 1):
        sheet.column_dimensions[get_column_letter(index)].width = min(
            48,
            max(16, max(
                (len(str(sheet.cell(row, index).value or ""))
                 for row in range(1, sheet.max_row + 1)),
                default=16,
            ) + 2),
        )

    if rows and table_name:
        table = Table(
            displayName=table_name,
            ref=f"A1:{get_column_letter(len(headers))}{len(rows) + 1}",
        )
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)


def _job_row(job):
    score = job.get("match_score")
    return [
        job.get("company", ""),
        job.get("title", ""),
        job.get("location", ""),
        job.get("experience", ""),
        round(float(score), 2) if score is not None else None,
        ", ".join(job.get("matching_skills", [])),
        ", ".join(job.get("missing_skills", [])),
        job.get("employment_type", ""),
        job.get("posted", ""),
        job.get("scraped_at", ""),
        str(job.get("description", ""))[:32767],
        job.get("job_url", ""),
        "",
    ]


def export_company_careers_report(
    jobs,
    company_results,
    minimum_score=70,
    output_path=DEFAULT_OUTPUT_PATH,
    job_errors=None,
):
    """Write all jobs and strict-above-threshold matches to an Excel workbook."""
    jobs = sorted(
        jobs,
        key=lambda job: job.get("match_score", 0),
        reverse=True,
    )
    matched_jobs = [
        job for job in jobs
        if job.get("match_score") is not None
        and job["match_score"] > minimum_score
    ]

    workbook = Workbook()
    matched_sheet = workbook.active
    matched_sheet.title = "Matched Jobs"
    _format_sheet(
        matched_sheet,
        JOB_HEADERS,
        [_job_row(job) for job in matched_jobs],
        table_name="CompanyMatchedJobs",
    )
    all_sheet = workbook.create_sheet("All Jobs")
    _format_sheet(
        all_sheet,
        JOB_HEADERS,
        [_job_row(job) for job in jobs],
        table_name="CompanyAllJobs",
    )

    summary_headers = [
        "Company",
        "Careers URL",
        "Status",
        "Pages Visited",
        "Jobs Found",
        f"Jobs Above {minimum_score}%",
        "Details",
    ]
    summary_rows = []
    for result in company_results:
        summary_rows.append([
            result.get("company", ""),
            result.get("careers_url", ""),
            result.get("status", ""),
            result.get("pages_visited", 0),
            result.get("jobs_found", 0),
            result.get("matched_jobs", 0),
            result.get("details", ""),
        ])
    summary_sheet = workbook.create_sheet("Company Summary")
    _format_sheet(
        summary_sheet,
        summary_headers,
        summary_rows,
        table_name="CompanyCareersSummary",
    )

    skills_rows = []
    for job in jobs:
        for skill in job.get("matching_skills", []):
            skills_rows.append([
                job.get("company", ""),
                job.get("title", ""),
                skill,
                "Matched",
                job.get("match_score"),
                job.get("job_url", ""),
            ])
        for skill in job.get("missing_skills", []):
            skills_rows.append([
                job.get("company", ""),
                job.get("title", ""),
                skill,
                "Missing",
                job.get("match_score"),
                job.get("job_url", ""),
            ])
    skills_sheet = workbook.create_sheet("Skills Analysis")
    skills_headers = [
        "Company",
        "Job Title",
        "Skill",
        "Candidate Match",
        "Match Score (%)",
        "Job URL",
    ]
    _format_sheet(
        skills_sheet,
        skills_headers,
        skills_rows,
        table_name="CompanySkillsAnalysis",
    )
    if skills_rows:
        skills_sheet.conditional_formatting.add(
            f"E2:E{len(skills_rows) + 1}",
            ColorScaleRule(
                start_type="num",
                start_value=0,
                start_color="F8696B",
                mid_type="num",
                mid_value=60,
                mid_color="FFEB84",
                end_type="num",
                end_value=100,
                end_color="63BE7B",
            ),
        )

    error_rows = [
        [
            error.get("company", ""),
            error.get("job_url", ""),
            error.get("error", ""),
        ]
        for error in (job_errors or [])
    ]
    error_sheet = workbook.create_sheet("Scrape Errors")
    _format_sheet(
        error_sheet,
        ["Company", "Job URL", "Error"],
        error_rows,
        table_name="CompanyScrapeErrors",
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    print(
        f"Company careers report saved: {output_path} "
        f"({len(matched_jobs)} jobs above {minimum_score}%)."
    )
    return output_path
