from src.ingestion.naukri_browser import NaukriBrowser


print("\n========== NAUKRI BROWSER TEST ==========")

browser = NaukriBrowser()

try:
    print("\nStarting browser...")

    browser.start()

    print("Browser started successfully.")

    print("\nSearching for Data Analyst jobs in Remote...")

    browser.search_jobs(
        role="Data Analyst",
        location="Remote"
    )

    print("\nSearch completed.")

    jobs = browser.get_job_cards()

    print(f"\nJobs found: {len(jobs)}")

    print("\n========== JOB CARDS ==========")

    for index, job in enumerate(jobs[:5], start=1):
        print(f"\n--- Job {index} ---")
        print(f"Title:      {job.get('title')}")
        print(f"Company:    {job.get('company')}")
        print(f"Location:   {job.get('location')}")
        print(f"Experience: {job.get('experience')}")
        print(f"Posted:     {job.get('posted')}")
        print(f"URL:        {job.get('job_url')}")

finally:
    browser.close()

print("\n========== TEST COMPLETED ==========")