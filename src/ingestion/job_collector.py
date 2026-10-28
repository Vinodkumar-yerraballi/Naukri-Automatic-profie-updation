
from src.extraction.jd_extractor import JDExtractor
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository


class JobCollector:
    """
    Collects jobs, extracts job information,
    evaluates jobs, and stores them.
    """

    def __init__(
        self,
        evaluator: JobEvaluator,
        repository: JobRepository
    ):
        self.evaluator = evaluator
        self.repository = repository

    def process_job(
        self,
        job_description: str,
        job_url: str,
        source: str = "TEST",
        job_metadata: dict = None
    ) -> dict:

        # Extract information from the job description.
        extractor = JDExtractor(job_description)
        job = extractor.extract_all()
        print("\nDEBUG — Extracted technical skills:", job.get("skills"))
        print("\nDEBUG — General requirements:", job.get("general_requirements"))

        # Add URL and source.
        job["job_url"] = job_url
        job["source"] = source

        # Preserve browser-extracted metadata.
        if job_metadata:
            for field in (
                "title",
                "company",
                "posted",
                "location",
                "experience",
                "employment_type",
                "education",
            ):
                if job_metadata.get(field):
                    job[field] = job_metadata[field]

        # Keep the database-compatible description.
        job["description"] = job.get("job_description", "")

        # Reject jobs outside the candidate's experience range.
        experience_result = (
            self.evaluator.experience_matcher.get_match_result(
                job.get("experience", "")
            )
        )

        if not experience_result["match"]:
            return {
                "job": job,
                "evaluation": None,
                "inserted": False,
                "updated": False,
                "skipped": True,
                "skip_reason": "Experience requirement does not match",
                "experience_match": experience_result,
            }

        # Evaluate eligible jobs.
        evaluation = self.evaluator.evaluate(job)
        job["match_score"] = evaluation["final_score"]

        # Store or update the job.
        existing_job = self.repository.job_exists(job["job_url"])

        if existing_job:
            updated = self.repository.update_job(job)

            return {
                "job": job,
                "evaluation": evaluation,
                "inserted": False,
                "updated": updated,
                "skipped": False,
            }

        inserted = self.repository.add_job(job)

        return {
            "job": job,
            "evaluation": evaluation,
            "inserted": inserted,
            "updated": False,
            "skipped": False,
        }
