import main

from src.ingestion.shine_job_search import ShineJobSearch


def test_shine_search_url_and_location_are_normalized_without_inference():
    assert ShineJobSearch._search_url("Data Analyst", "Bangalore") == (
        "https://www.shine.com/job-search/"
        "data-analyst-jobs-in-bangalore"
    )
    assert ShineJobSearch._find_location(
        "Data Analyst posted 5 hours ago in Bengaluru",
        "Bangalore",
    ) == "Bangalore"
    assert ShineJobSearch._find_location(
        "Data Analyst posted 5 hours ago in Coimbatore",
        "Bangalore",
    ) == ""


def test_shine_description_extractor_requires_a_delimited_full_description():
    description = (
        "Analyze source data, build dashboards, and share findings "
        "with business stakeholders. " * 5
    )
    page_text = (
        f"Data Analyst\nJob Description\n{description}\n\n"
        "Industry\nInformation Technology"
    )

    assert ShineJobSearch._extract_job_description(page_text) == (
        description.strip()
    )
    assert ShineJobSearch._extract_job_description(
        "Data Analyst\nSkills\nSQL"
    ) == ""
    assert ShineJobSearch._extract_job_description(
        "Job Description\nShort text"
    ) == ""


def test_shine_search_only_creates_drafts_at_configured_match_threshold(
    monkeypatch,
    capsys,
):
    class ConfigManager:
        def get_job_search_config(self):
            return {
                "roles": ["Data Analyst"],
                "locations": ["Bangalore"],
                "max_searches_per_run": 1,
                "max_jobs_per_run": 5,
                "posted_within_hours": 24,
                "experience": {"minimum": 0, "maximum": 2},
            }

        def get_resume_tailoring_config(self):
            return {}

        def get_minimum_score(self):
            return 75

    class ProfileManager:
        def __init__(self, path):
            assert path == "config/profile.yaml"

        def load_profile(self):
            pass

        def get_all_skills(self):
            return ["SQL", "Python"]

        def get_target_roles(self):
            return ["Data Analyst"]

        def get_education(self):
            return []

    class JobCollector:
        def __init__(self, evaluator, repository, allow_unknown_experience):
            assert allow_unknown_experience is True

        def process_job(self, **job):
            score = 80 if job["job_metadata"]["title"] == "Strong match" else 74
            processed = dict(job["job_metadata"])
            processed["description"] = job["job_description"]
            processed["match_score"] = score
            return {
                "job": processed,
                "evaluation": {"final_score": score},
                "inserted": True,
                "updated": False,
                "skipped": False,
            }

    class Browser:
        def __init__(self, headless):
            assert headless is False
            self.closed = False

        def start(self):
            pass

        def search_jobs(
            self,
            role,
            location,
            posted_within_hours,
            max_results=None,
        ):
            assert (role, location, posted_within_hours) == (
                "Data Analyst",
                "Bangalore",
                24,
            )
            assert max_results == 5
            return [
                {
                    "job_url": "https://www.shine.com/jobs/1",
                    "title": "Strong match",
                    "company": "Example",
                    "location": "Bangalore",
                    "experience": "1 to 2 years",
                    "posted": "5 hours ago",
                    "description": "Complete job description " * 10,
                    "description_is_complete": True,
                },
                {
                    "job_url": "https://www.shine.com/jobs/2",
                    "title": "Near threshold",
                    "company": "Other",
                    "location": "Bangalore",
                    "experience": "1 to 2 years",
                    "posted": "5 hours ago",
                    "description": "Complete job description " * 10,
                    "description_is_complete": True,
                },
            ]

        def close(self):
            self.closed = True

    class Tailoring:
        def __init__(self):
            self.drafts = []

        def create_draft(self, job):
            self.drafts.append(job["title"])
            return f"drafts/{job['title']}.docx"

    tailoring = Tailoring()
    monkeypatch.setattr(main, "ConfigManager", ConfigManager)
    monkeypatch.setattr(main, "ProfileManager", ProfileManager)
    monkeypatch.setattr(main, "JobEvaluator", lambda **kwargs: kwargs)
    monkeypatch.setattr(main, "JobRepository", lambda: object())
    monkeypatch.setattr(main, "JobCollector", JobCollector)
    monkeypatch.setattr(main, "ShineJobSearch", Browser)
    monkeypatch.setattr(
        main.ResumeTailoringService,
        "from_config",
        lambda config: tailoring,
    )

    main.run_shine_search()

    output = capsys.readouterr().out
    assert tailoring.drafts == ["Strong match"]
    assert "resume match score: 80.0%" in output
    assert "resume match score: 74.0%" in output
    assert "No applications were submitted." in output
