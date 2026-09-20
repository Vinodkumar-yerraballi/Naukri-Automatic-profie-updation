from datetime import datetime
from src.database.db import JobDataBase

class JobRepository:
    """
    Handles storing and retrieving jobs from the database.
    """
    def __init__(self,database_path="data/job_automation.db"):
        self.database=JobDataBase(database_path)
        #make sure table exist
        self.database.create_table()
    def job_exists(self,job_url:str)->bool:
        """
        Check whether a job already exists
        using its unique URL.
        """
        connection = self.database.get_connection()
        cursor= connection.cursor()
        cursor.execute(
            """
            SELECT id 
            FROM jobs
            WHERE job_url=?
            """,
            (job_url,)
        )
        result= cursor.fetchone()
        connection.close()
        return result is not None
    def add_job(self,job:dict)->bool:
        """
        Add a new job to the database.

        Returns:
            True  -> job inserted
            False -> job already exists
        """
        if self.job_exists(job["job_url"]):
            return False
        connection = self.database.get_connection()
        cursor=connection.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (
                title,
                company,
                location,
                experience,
                job_url,
                description,
                skills,
                match_score,
                status,
                source,
                date_found
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("experience"),
                job.get("job_url"),
                job.get("description"),
                ", ".join(job.get("skills", [])),
                job.get("match_score"),
                job.get("status", "FOUND"),
                job.get("source"),
                datetime.now().isoformat()
            )
        )
        connection.commit()
        connection.close()
        return True
    def get_job_by_url(self,job_url:str):
        """
        Retrieve a job using its URL.
        """
        connection= self.database.get_connection()
        connection.row_factory=__import__(
            "sqlite3"
        ).Row
        cursor=connection.cursor()
        cursor.execute(
            """
            SELECT *
            FROM jobs
            WHERE job_url = ?
            """,
            (job_url,)
        )
        job=cursor.fetchone()
        connection.close()
        if job:
            return dict(job)
        return None
    def update_match_score(self,job_url:str,score:float):
        """
        Update the match score
        """
        connection= self.database.get_connection()
        cursor= connection.cursor()
        cursor.execute(
            """
            UPDATE jobs
            SET match_score = ?
            WHERE job_url = ?
            """,
            (score, job_url)
        )
        connection.commit()
        connection.close()
    def update_status(self,job_url:str,status:str):
        """
        Update job/application status.
        """
        connection= self.database.get_connection()
        cursor=connection.cursor()
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?
            WHERE job_url = ?
            """,
            (status, job_url)
        )
        connection.commit()
        connection.close()
    def get_all_jobs(self):
        """
        Return all jobs stored in the database.
        """
        connection=self.database.get_connection()
        connection.row_factory=__import__(
            "sqlite3"
        ).Row
        cursor=connection.cursor()
        cursor.execute(
            """
            SELECT *
            FROM jobs
            ORDER BY id DESC
            """

        )
        jobs=cursor.fetchall()
        connection.close()
        return [dict(job) for job in jobs]

