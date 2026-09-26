from src.ingestion.naukri_browser import NaukriBrowser
from src.extraction.jd_extractor import JDExtractor


def main():
    browser = NaukriBrowser()

    try:
        # Start browser
        browser.start()

        # Open Naukri search page
        browser.search_jobs("Data Analyst", "Remote")

        # Extract job cards from search results
        jobs = browser.get_job_cards()

        print(f"\nTotal jobs found: {len(jobs)}")

        if not jobs:
            print("No jobs found.")
            return

        # Select first job
        job = jobs[0]

        print("\n========== SELECTED JOB ==========")
        print(f"Title     : {job.get('title')}")
        print(f"Company   : {job.get('company')}")
        print(f"Location  : {job.get('location')}")
        print(f"Experience: {job.get('experience')}")
        print(f"URL       : {job.get('job_url')}")
        print("===================================")

        # Extract complete job details
        job = browser.extract_job_details(job)

        job_description = job.get("job_description", "")

        print("\n========== JD LENGTH ==========")
        print(f"Description length: {len(job_description)}")
        print("===============================")

        # Extract skills from the real JD
        extractor = JDExtractor(job_description)

        extracted_skills = extractor.extract_skills()

        print("\n========== EXTRACTED SKILLS ==========")

        if extracted_skills:
            for skill in extracted_skills:
                print(f"✓ {skill}")
        else:
            print("No skills extracted.")

        print(f"\nTotal extracted skills: {len(extracted_skills)}")
        print("======================================")

        # Print raw JD for debugging
        print("\n========== RAW JOB DESCRIPTION ==========")
        print(job_description[:5000])
        print("=========================================")

    finally:
        browser.close()


if __name__ == "__main__":
    main()