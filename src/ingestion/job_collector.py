from src.extraction.jd_extractor import JDExtractor
from src.matching.job_evaluator import JobEvaluator
from src.database.job_repository import JobRepository

class JobCollector:
    """
    Collects jobs, extracts job information,
    evaluates jobs, and stores them.
    """
    def __init__(self,
                evaluator:JobEvaluator,
                repository:JobRepository):
        self.evaluator=evaluator
        self.repository=repository
    def process_job(self,job_description:str,job_url:str,source:str ="TEST")-> dict:
        """
        Process a single job description.
        """

        # 1 Extract the Job description
        extractor=JDExtractor(job_description)
        job=extractor.extract_all()

        #  ADD URL and Source
        job["job_url"]= job_url
        job["source"]=source

        # Step 2: Evaluation job
        evaluation = self.evaluator.evaluate(job)

        # Add evaluation information 
        job["match_score"]=evaluation["final_score"]
        job["status"] = (
            "MATCHED"
            if evaluation["final_score"] >=70
            else "NOT_MATCHED"
        )

        # step 3: store job
        inserted=self.repository.add_job(job)
        return {
            "job":job,
            "evaluation": evaluation,
            "inserted" : inserted
        }