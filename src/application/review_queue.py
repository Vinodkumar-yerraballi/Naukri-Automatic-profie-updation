from src.database.job_repository import JobRepository
from src.application.application_tracker import ApplicationTracker


class ReviewQueue:
    """
    Handles jobs that are waiting for user review.
    """

    def __init__(
        self,
        repository: JobRepository,
        application_tracker: ApplicationTracker
    ):
        self.repository = repository
        self.application_tracker = application_tracker

    def get_pending_jobs(self) -> list:
        """
        Return all jobs currently waiting for review.
        """
        return self.repository.get_review_jobs()

    def approve_job(self, job_url: str) -> bool:
        """
        Approve a job waiting for review.
        """

        job = self.repository.get_job_by_url(job_url)

        if not job:
            return False

        if job.get("status") != "REVIEW":
            return False

        self.application_tracker.mark_approved(job_url)
        return True

    def reject_job(self, job_url: str) -> bool:
        """
        Reject a job waiting for review.
        """

        job = self.repository.get_job_by_url(job_url)

        if not job:
            return False

        if job.get("status") != "REVIEW":
            return False

        self.application_tracker.mark_rejected(job_url)
        return True

    def display_pending_jobs(self) -> None:
        """
        Display jobs currently waiting for review.
        """

        jobs = self.get_pending_jobs()

        print("\n========== REVIEW QUEUE ==========")

        if not jobs:
            print("No jobs are waiting for review.")
            return

        for index, job in enumerate(jobs, start=1):
            print(f"\n[{index}] {job.get('title', 'Unknown')}")
            print(f"Company: {job.get('company', 'Unknown')}")
            print(f"Location: {job.get('location', 'Unknown')}")
            print(f"Experience: {job.get('experience', 'Unknown')}")
            print(f"Match Score: {job.get('match_score', 0)}")
            print(f"Source: {job.get('source', 'Unknown')}")
            print(f"URL: {job.get('job_url', '')}")
            print(f"Status: {job.get('status', 'UNKNOWN')}")

        print("\n==================================")
        print(f"Total jobs waiting for review: {len(jobs)}")

    def review_jobs_interactively(self) -> None:
        """
        Allow the user to manually review pending jobs.
        """

        while True:
            jobs = self.get_pending_jobs()

            if not jobs:
                print("\nNo jobs are waiting for review.")
                return

            print("\n========== REVIEW QUEUE ==========")

            for index, job in enumerate(jobs, start=1):
                print(
                    f"[{index}] "
                    f"{job.get('title', 'Unknown')} | "
                    f"{job.get('company', 'Unknown')} | "
                    f"Score: {job.get('match_score', 0)}"
                )

            print("\nEnter the job number to review.")
            print("Enter Q to exit.")

            choice = input("Your choice: ").strip().lower()

            if choice == "q":
                print("\nReview queue closed.")
                return

            if not choice.isdigit():
                print("Invalid choice. Please enter a job number.")
                continue

            job_index = int(choice)

            if job_index < 1 or job_index > len(jobs):
                print("Invalid job number.")
                continue

            selected_job = jobs[job_index - 1]

            print("\n========== SELECTED JOB ==========")
            print(f"Title: {selected_job.get('title', 'Unknown')}")
            print(f"Company: {selected_job.get('company', 'Unknown')}")
            print(f"Location: {selected_job.get('location', 'Unknown')}")
            print(f"Experience: {selected_job.get('experience', 'Unknown')}")
            print(f"Match Score: {selected_job.get('match_score', 0)}")
            print(f"Source: {selected_job.get('source', 'Unknown')}")
            print(f"URL: {selected_job.get('job_url', '')}")
            print("==================================")

            print("\n[A] Approve")
            print("[R] Reject")
            print("[S] Skip")

            action = input("Your decision: ").strip().lower()

            if action == "a":
                success = self.approve_job(selected_job["job_url"])

                if success:
                    print("\nJob approved successfully.")
                else:
                    print("\nUnable to approve this job.")

            elif action == "r":
                success = self.reject_job(selected_job["job_url"])

                if success:
                    print("\nJob rejected successfully.")
                else:
                    print("\nUnable to reject this job.")

            elif action == "s":
                print("\nJob skipped.")

            else:
                print("\nInvalid action.")