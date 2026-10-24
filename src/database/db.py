import sqlite3
from pathlib import Path

class JobDataBase:
    """"
    A class to manage the SQLite database for job data.
    """

    def __init__(self, database_path: str = "data/job_automation.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
    def get_connection(self):
        """
        Establish a connection to the SQLite database.
        Returns:
            sqlite3.Connection: A connection object to the SQLite database.
        """
        return sqlite3.connect(self.database_path)

    def create_table(self):
        """
        Create the jobs table in the database
        """
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,

                company TEXT,

                location TEXT,

                experience TEXT,

                job_url TEXT UNIQUE,

                description TEXT,

                skills TEXT,

                match_score REAL,

                status TEXT DEFAULT 'FOUND',

                source TEXT,

                date_found TEXT,

                date_applied TEXT,

                date_application_attempted TEXT
            )
            """)
        cursor.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        if "date_application_attempted" not in columns:
            cursor.execute(
                "ALTER TABLE jobs ADD COLUMN date_application_attempted TEXT"
            )
        connection.commit()
        connection.close()

    def get_job_count(self):
        """
        Return the total number of jobs stored
        """
        connection = self.get_connection()
        cursor=connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM jobs"
        )
        count = cursor.fetchone()[0]
        connection.close()
        return count
