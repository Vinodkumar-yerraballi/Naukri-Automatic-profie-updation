from src.ingestion.naukri_browser import NaukriBrowser
from src.extraction.jd_extractor import JDExtractor


def main():

    browser = NaukriBrowser()

    try:
        # ============================================================
        # 1. START BROWSER
        # ============================================================

        browser.start()

        # ============================================================
        # 2. SEARCH JOBS
        # ============================================================

        browser.search_jobs("Data Analyst", "Remote")

        # ============================================================
        # 3. GET JOB CARDS
        # ============================================================

        jobs = browser.get_job_cards()

        print(f"\nTotal jobs found: {len(jobs)}")

        if not jobs:
            print("No jobs found.")
            return

        # ============================================================
        # 4. SELECT FIRST JOB
        # ============================================================

        job = None

        for item in jobs:
            company = item.get("company", "").lower()

            if "peroptyx" in company:
                job = item
                break

        if job is None:
            print("Peroptyx job not found.")
            return

        print("\n========== SELECTED JOB ==========")
        print(f"Title     : {job.get('title')}")
        print(f"Company   : {job.get('company')}")
        print(f"Location  : {job.get('location')}")
        print(f"Experience: {job.get('experience')}")
        print(f"URL       : {job.get('job_url')}")
        print("===================================")

        # ============================================================
        # 5. EXTRACT COMPLETE JOB DETAILS
        # ============================================================

        job = browser.extract_job_details(job)

        job_description = job.get("job_description", "")

        print("\n========== JD LENGTH ==========")
        print(f"Description length: {len(job_description)}")
        print("===============================")

        # ============================================================
        # 6. CREATE JD EXTRACTOR
        # ============================================================

        extractor = JDExtractor(job_description)

        # ============================================================
        # 7. EXTRACT SKILLS
        # ============================================================

        skill_result = extractor.extract_skills()

        technical_skills = skill_result["technical_skills"]
        general_requirements = skill_result["general_requirements"]

        # ============================================================
        # 8. DISPLAY TECHNICAL SKILLS
        # ============================================================

        print("\n========== TECHNICAL SKILLS ==========")

        if technical_skills:

            for skill in technical_skills:
                print(f"✓ {skill}")

        else:
            print("No technical skills extracted.")

        print(
            f"\nTotal technical skills: "
            f"{len(technical_skills)}"
        )

        print("======================================")

        # ============================================================
        # 9. DISPLAY GENERAL REQUIREMENTS
        # ============================================================

        print("\n========== GENERAL REQUIREMENTS ==========")

        if general_requirements:

            for requirement in general_requirements:
                print(f"✓ {requirement}")

        else:
            print("No general requirements extracted.")

        print(
            f"\nTotal general requirements: "
            f"{len(general_requirements)}"
        )

        print("==========================================")

        # ============================================================
        # 10. EXTRACT ALL JOB INFORMATION
        # ============================================================

        job_details = extractor.extract_all()

        print("\n========== EXTRACTED JOB DETAILS ==========")

        print(f"Title      : {job_details['title']}")
        print(f"Company    : {job_details['company']}")
        print(f"Location   : {job_details['location']}")
        print(f"Experience : {job_details['experience']}")

        print("\nTechnical Skills:")
        for skill in job_details["technical_skills"]:
            print(f"  - {skill}")

        print("\nGeneral Requirements:")
        for requirement in job_details["general_requirements"]:
            print(f"  - {requirement}")

        print("===========================================")

        # ============================================================
        # 11. RAW JOB DESCRIPTION
        # ============================================================

        print("\n========== RAW JOB DESCRIPTION ==========")
        print(job_description[:5000])
        print("=========================================")

    finally:

        # ============================================================
        # 12. CLOSE BROWSER
        # ============================================================

        browser.close()


if __name__ == "__main__":
    main()