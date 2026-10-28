from src.ingestion.naukri_browser import NaukriBrowser


print("\n========== NAUKRI JOB DETAILS TEST ==========")

browser = NaukriBrowser()

try:
    browser.start()

    browser.search_jobs(
        role="Data Analyst",
        location="Remote"
    )

    jobs = browser.get_job_cards()

    print(f"\nJobs found: {len(jobs)}")

    if not jobs:
        print("No jobs found.")
    else:
        job = jobs[1]

        print("\n========== SELECTED JOB ==========")
        print(f"Title:      {job.get('title')}")
        print(f"Company:    {job.get('company')}")
        print(f"Location:   {job.get('location')}")
        print(f"Experience: {job.get('experience')}")
        print(f"URL:        {job.get('job_url')}")

        print("\n========== EXTRACTING JOB DETAILS ==========")

        job = browser.extract_job_details(job)

        print("\n========== EXTRACTED DETAILS ==========")

        print("\nJob description length:")
        print(len(job.get("job_description", "")))

        print("\nJob description:")
        print(job.get("job_description", "")[:5000])

        print("\nEmployment type:")
        print(job.get("employment_type"))

        print("\nEducation:")
        print(job.get("education"))

        print("\nExperience:")
        print(job.get("experience"))

        print("\nSecurity challenge:")
        print(job.get("security_challenge"))

finally:
    browser.close()

print("\n========== TEST COMPLETED ==========")