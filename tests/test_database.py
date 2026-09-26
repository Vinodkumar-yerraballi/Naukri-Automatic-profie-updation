from src.database.job_repository import JobRepository


def main():
    print("\n========== UPDATE JOB TEST ==========")

    repository = JobRepository()

    job_url = (
        "https://www.naukri.com/job-listings-data-analyst-"
        "berg-technologies-bengaluru-2-to-4-years-070426015264"
    )

    updated_job = {
        "title": "Data Analyst - Updated",
        "company": "Berg Technologies Private Limited",
        "location": "Remote",
        "experience": "0-2 Yrs",
        "description": "Updated job description",
        "skills": ["Python", "SQL", "Power BI"],
        "match_score": 95.0,
        "status": "MATCHED",
        "source": "Naukri",
        "job_url": job_url
    }

    result = repository.update_job(updated_job)

    print(f"Update result: {result}")

    job = repository.get_job_by_url(job_url)

    print("\nUpdated job:")
    print(f"Title: {job['title']}")
    print(f"Company: {job['company']}")
    print(f"Location: {job['location']}")
    print(f"Experience: {job['experience']}")
    print(f"Match Score: {job['match_score']}")
    print(f"Status: {job['status']}")
    print(f"Skills: {job['skills']}")

    print("\n========== TEST COMPLETED ==========")


if __name__ == "__main__":
    main()