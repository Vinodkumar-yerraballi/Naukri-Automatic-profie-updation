from src.ingestion.job_collector import JobCollector
from src.application.application_workflow import ApplicationWorkflow

class JobPipeline:
    """
    Coordinates job collection and application workflow.
    """
    def __init__(self,job_collector:JobCollector,application_workflow:ApplicationWorkflow):
        self.job_collector=job_collector
        self.application_workflow=application_workflow

    def process_job(self,
                    job_description:str,
                    job_url:str,
                    source:str = "TEST",
                    page_text:str=" ")->dict:
        """
        Process a single job from collection
        through the application workflow.
        """
        # Step 1: Collect and evaluate the job
        collected_job=self.job_collector.process_job(
            job_description=job_description,
            job_url=job_url,
            source=source
        )

        job=collected_job["job"]

        # Step 2: Send job through the application flow

        workflow_result=self.application_workflow.process_job(
            job=job,
            page_text=page_text
        )
        return {
            "job":job,
            "evaluation":collected_job["evaluation"],
            "inserted":collected_job["inserted"],
            "updated":collected_job["updated"],
            "workflow":workflow_result
        }

    def process_multiple_jobs(self,jobs:list)->list:
        """
        Process multiple jobs.

        Each item in jobs should contain:

        {
            "job_description": "...",
            "job_url": "...",
            "source": "...",
            "page_text": "..."
        }
        """

        results=[]
        for job_data in jobs:
            result=self.process_job(
                job_description=job_data.get(
                    "job_description",""
                ),
                job_url=job_data.get("job_url",""),
                source=job_data.get("source","TEST"),
                page_text=job_data.get("page_text","")

            )
            results.append(result)
        return results


