from src.extraction.jd_extractor import JDExtractor
from src.ingestion.naukri_browser import NaukriBrowser


def test_skill_extraction_combines_key_skills_and_full_description():
    description = """
    Key Skills
    Python, SQL
    Role: Data Engineer
    Build pipelines with AWS Glue, AWS Lambda, Apache Airflow, and Redshift.
    """

    extracted = JDExtractor(description).extract_all()

    assert extracted["skills"] == [
        "Python",
        "SQL",
        "Redshift",
        "Apache Airflow",
        "Airflow",
        "AWS",
        "Lambda",
        "Glue",
    ]


def test_skill_extraction_does_not_match_substrings_in_key_skills():
    description = """
    Key Skills
    MySQL
    Role: Data Analyst
    """

    extracted = JDExtractor(description).extract_all()

    assert "SQL" not in extracted["skills"]
    assert "MySQL" in extracted["skills"]


def test_description_quality_detects_naukri_page_interface_text():
    issues = NaukriBrowser._description_quality_issues(
        "Data Analyst role. ResdexAI REXPremiumXReportsSearchProfiles "
        "Post a job. The description follows."
    )

    assert issues == ["Page interface text detected: resdexai"]


def test_description_quality_accepts_normal_job_description():
    issues = NaukriBrowser._description_quality_issues(
        "Data Analyst role using Python and SQL to build reporting."
    )

    assert issues == []


def test_skill_aliases_are_not_double_counted_in_job_match():
    from src.matching.skill_matcher import SkillMatcher

    result = SkillMatcher(["Apache Airflow"]).get_match_result(
        ["Apache Airflow", "Airflow"]
    )

    assert result["matched_skills"] == ["Apache Airflow"]
    assert result["missing_skills"] == []
    assert result["match_percentage"] == 100.0
