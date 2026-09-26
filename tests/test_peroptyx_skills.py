from src.ingestion.naukri_browser import NaukriBrowser
from src.extraction.jd_extractor import JDExtractor


def main():

    browser = NaukriBrowser()

    try:
        browser.start()

        browser.search_jobs("Data Analyst", "Remote")

        jobs = browser.get_job_cards()

        print(f"\nJobs found: {len(jobs)}")

        # Find Peroptyx job
        selected_job = None

        for job in jobs:
            if "peroptyx" in job.get("company", "").lower():
                selected_job = job
                break

        if selected_job is None:
            print("Peroptyx job not found.")
            return

        print("\n========== SELECTED JOB ==========")
        print(f"Title      : {selected_job.get('title')}")
        print(f"Company    : {selected_job.get('company')}")
        print(f"Location   : {selected_job.get('location')}")
        print(f"Experience : {selected_job.get('experience')}")
        print(f"URL        : {selected_job.get('job_url')}")
        print("===================================")

        # Extract complete job details
        selected_job = browser.extract_job_details(selected_job)

        description = selected_job.get("job_description", "")

        print("\n========== JD LENGTH ==========")
        print(len(description))
        print("===============================")

        # Run JD extractor
        extractor = JDExtractor(description)

        skills = extractor.extract_skills()

        print("\n========== EXTRACTED SKILLS ==========")

        if skills:
            for skill in skills:
                print(f"✓ {skill}")
        else:
            print("No recognized skills found.")

        print(f"\nTotal skills: {len(skills)}")
        print("======================================")

        print("\n========== KEY SKILLS SECTION ==========")

        key_skills_match = description.split("Key Skills", 1)

        if len(key_skills_match) > 1:
            key_skills = key_skills_match[1]
            print(key_skills.strip())
        else:
            print("Key Skills section not found.")

        print("========================================")

    finally:
        browser.close()


if __name__ == "__main__":
    main()