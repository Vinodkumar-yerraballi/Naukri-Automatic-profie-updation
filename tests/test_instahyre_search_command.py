import main


def test_instahyre_search_command_stores_jobs_without_applying(monkeypatch):
    class ConfigManager:
        def get_job_search_config(self):
            return {
                "roles": ["Data Analyst"],
                "locations": ["Bangalore"],
                "work_modes": ["Hybrid"],
                "experience": {"minimum": 0, "maximum": 2},
                "max_searches_per_run": 1,
                "max_jobs_per_run": 1,
            }

    class ProfileManager:
        def __init__(self, path):
            assert path == "config/profile.yaml"

        def load_profile(self):
            pass

        def get_all_skills(self):
            return ["SQL"]

        def get_target_roles(self):
            return ["Data Analyst"]

        def get_education(self):
            return ["Bachelor's"]

    class JobRepository:
        pass

    class JobCollector:
        def __init__(
            self,
            evaluator,
            repository,
            allow_unknown_experience=False,
        ):
            assert allow_unknown_experience is True
            self.evaluator = evaluator
            self.repository = repository
            self.processed = []
            collectors.append(self)

        def process_job(self, **job):
            self.processed.append(job)
            return {
                "inserted": True,
                "updated": False,
                "skipped": False,
            }

    class InstahyreBrowser:
        def __init__(self, headless):
            assert headless is False
            self.closed = False

        def start(self):
            pass

        def search_jobs(self, role, location):
            assert (role, location) == ("Data Analyst", "Bangalore")
            return [
                {
                    "job_url": "https://www.instahyre.com/job-1/",
                    "title": "Data Analyst",
                    "company": "Example",
                    "location": "Bangalore",
                    "description": "SQL and analytics",
                },
                {
                    "job_url": "https://www.instahyre.com/job-2/",
                    "title": "Data Analyst",
                    "company": "Other",
                    "location": "Bangalore",
                    "description": "SQL and reporting",
                },
            ]

        def close(self):
            self.closed = True

    collectors = []
    monkeypatch.setattr(main, "ConfigManager", ConfigManager)
    monkeypatch.setattr(main, "ProfileManager", ProfileManager)
    monkeypatch.setattr(main, "JobEvaluator", lambda **kwargs: kwargs)
    monkeypatch.setattr(main, "JobRepository", JobRepository)
    monkeypatch.setattr(main, "JobCollector", JobCollector)
    monkeypatch.setattr(main, "InstahyreBrowser", InstahyreBrowser)

    main.run_instahyre_search()

    assert len(collectors) == 1
    assert len(collectors[0].processed) == 1
    assert collectors[0].processed[0]["source"] == "Instahyre"
    assert collectors[0].processed[0]["job_url"] == (
        "https://www.instahyre.com/job-1/"
    )
