from src.extraction.jd_extractor import JDExtractor
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository
from src.config.config_manager import ConfigManager


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

        config_manager = ConfigManager()
        self.minimum_score = config_manager.get_minimum_score()

    def process_job(
        self,
        job_description: str,
        job_url: str,
        source: str = "TEST",
        job_metadata: dict = None
    ) -> dict:

        # Extract information from JD
        extractor = JDExtractor(job_description)

        job = extractor.extract_all()

        # Add URL and source
        job["job_url"] = job_url
        job["source"] = source

        # Preserve browser-extracted metadata
        if job_metadata:

            if job_metadata.get("title"):
                job["title"] = job_metadata["title"]

            if job_metadata.get("company"):
                job["company"] = job_metadata["company"]

            if job_metadata.get("location"):
                job["location"] = job_metadata["location"]

            if job_metadata.get("experience"):
                job["experience"] = job_metadata["experience"]

            if job_metadata.get("employment_type"):
                job["employment_type"] = (
                    job_metadata["employment_type"]
                )

            if job_metadata.get("education"):
                job["education"] = (
                    job_metadata["education"]
                )

        # Database-compatible description
        job["description"] = job.get(
            "job_description",
            ""
        )

        # Evaluate job
        evaluation = self.evaluator.evaluate(job)

        # Add score
        job["match_score"] = (
            evaluation["final_score"]
        )

        # Determine status
        job["status"] = (
            "MATCHED"
            if evaluation["final_score"]
            >= self.minimum_score
            else "NOT_MATCHED"
        )

        # Store job
        existing_job = self.repository.job_exists(job["job_url"])

        if existing_job:
            updated = self.repository.update_job(job)

            return {
                "job": job,
                "evaluation": evaluation,
                "inserted": False,
                "updated": updated
            }

        inserted = self.repository.add_job(job)

        return {
            "job": job,
            "evaluation": evaluation,
            "inserted": inserted,
            "updated": False
        }