from src.ingestion.naukri_browser import NaukriBrowser
from src.extraction.jd_extractor import JDExtractor
from src.profile.profile_updater import ProfileManager
from src.matching.skill_matcher import SkillMatcher


def main():

    browser = NaukriBrowser()

    try:
        # ============================================================
        # 1. LOAD CANDIDATE PROFILE
        # ============================================================

        profile = ProfileManager("config/profile.yaml")
        profile.load_profile()

        candidate_skills = profile.get_all_skills()

        print("\n========== CANDIDATE PROFILE ==========")

        for skill in candidate_skills:
            print(f"✓ {skill}")

        print(f"\nTotal candidate skills: {len(candidate_skills)}")
        print("=======================================")

        # ============================================================
        # 2. START BROWSER
        # ============================================================

        browser.start()

        # ============================================================
        # 3. SEARCH JOBS
        # ============================================================

        browser.search_jobs("Data Analyst", "Remote")

        jobs = browser.get_job_cards()

        print(f"\nJobs found: {len(jobs)}")

        if not jobs:
            print("No jobs found.")
            return

        # ============================================================
        # 4. SELECT NAGARRO JOB
        # ============================================================

        selected_job = None

        for job in jobs:

            company = job.get("company", "").lower()

            if "nagarro" in company:
                selected_job = job
                break

        if selected_job is None:
            print("Nagarro job not found.")
            return

        print("\n========== SELECTED JOB ==========")
        print(f"Title      : {selected_job.get('title')}")
        print(f"Company    : {selected_job.get('company')}")
        print(f"Location   : {selected_job.get('location')}")
        print(f"Experience : {selected_job.get('experience')}")
        print(f"URL        : {selected_job.get('job_url')}")
        print("===================================")

        # ============================================================
        # 5. EXTRACT JOB DETAILS
        # ============================================================

        selected_job = browser.extract_job_details(selected_job)

        description = selected_job.get(
            "job_description",
            ""
        )

        print("\n========== JD LENGTH ==========")
        print(f"{len(description)} characters")
        print("===============================")

        # ============================================================
        # 6. EXTRACT SKILLS
        # ============================================================

        extractor = JDExtractor(description)

        skill_result = extractor.extract_skills()

        technical_skills = skill_result[
            "technical_skills"
        ]

        general_requirements = skill_result[
            "general_requirements"
        ]

        print("\n========== TECHNICAL SKILLS ==========")

        for skill in technical_skills:
            print(f"• {skill}")

        print(
            f"\nTotal technical skills: "
            f"{len(technical_skills)}"
        )

        print("\n========== GENERAL REQUIREMENTS ==========")

        for requirement in general_requirements:
            print(f"• {requirement}")

        print(
            f"\nTotal general requirements: "
            f"{len(general_requirements)}"
        )

        # ============================================================
        # 7. MATCH TECHNICAL SKILLS
        # ============================================================

        matcher = SkillMatcher(candidate_skills)

        match_result = matcher.get_match_result(
            technical_skills
        )

        print("\n========== SKILL MATCH RESULT ==========")

        print("\nMatched Skills:")

        if match_result["matched_skills"]:

            for skill in match_result["matched_skills"]:
                print(f"✓ {skill}")

        else:
            print("None")

        print("\nMissing Skills:")

        if match_result["missing_skills"]:

            for skill in match_result["missing_skills"]:
                print(f"✗ {skill}")

        else:
            print("None")

        print(
            f"\nTechnical Skill Match: "
            f"{match_result['match_percentage']}%"
        )

        print("========================================")

    finally:

        browser.close()


if __name__ == "__main__":
    main()