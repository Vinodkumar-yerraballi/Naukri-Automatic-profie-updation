from src.ingestion.naukri_browser import NaukriBrowser
from src.extraction.jd_extractor import JDExtractor
from src.profile.profile_updater import ProfileManager
from src.matching.skill_matcher import SkillMatcher
from src.matching.experience_matcher import ExperienceMatcher
from src.matching.role_matcher import RoleMatcher
from src.matching.location_matcher import LocationMatcher


def main():

    browser = NaukriBrowser()

    try:
        profile = ProfileManager("config/profile.yaml")
        profile.load_profile()

        candidate_skills = profile.get_all_skills()
        candidate_roles = profile.get_target_roles()

        browser.start()

        browser.search_jobs("Data Analyst", "Remote")

        jobs = browser.get_job_cards()

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
        print("===================================")

        selected_job = browser.extract_job_details(selected_job)

        description = selected_job.get("job_description", "")

        extractor = JDExtractor(description)

        skill_result = extractor.extract_skills()

        technical_skills = skill_result["technical_skills"]

        print("\n========== EXTRACTED KEY SKILLS ==========")

        for skill in technical_skills:
            print(f"• {skill}")

        print(f"\nTotal: {len(technical_skills)}")

        # --------------------------------------------------------
        # Skill matching
        # --------------------------------------------------------

        skill_matcher = SkillMatcher(candidate_skills)

        skill_result = skill_matcher.get_match_result(
            technical_skills
        )

        print("\n========== SKILL MATCH ==========")

        print(
            f"Matched: "
            f"{skill_result['matched_skills']}"
        )

        print(
            f"Missing: "
            f"{skill_result['missing_skills']}"
        )

        print(
            f"Skill Percentage: "
            f"{skill_result['match_percentage']}"
        )

        # --------------------------------------------------------
        # Role matching
        # --------------------------------------------------------

        role_matcher = RoleMatcher(candidate_roles)

        role_match = role_matcher.is_role_match(
            selected_job.get("title", "")
        )

        print("\n========== ROLE MATCH ==========")
        print(f"Role Match: {role_match}")

        # --------------------------------------------------------
        # Experience matching
        # --------------------------------------------------------

        experience_matcher = ExperienceMatcher(
            candidate_min=0,
            candidate_max=2
        )

        experience_match = experience_matcher.is_experience_match(
            selected_job.get("experience", "")
        )

        print("\n========== EXPERIENCE MATCH ==========")
        print(
            f"Job Experience: "
            f"{selected_job.get('experience')}"
        )
        print(f"Experience Match: {experience_match}")

        # --------------------------------------------------------
        # Location matching
        # --------------------------------------------------------

        location_matcher = LocationMatcher(
            ["Remote", "Bangalore", "Hyderabad", "Chennai"]
        )

        location_match = location_matcher.is_location_match(
            selected_job.get("location", "")
        )

        print("\n========== LOCATION MATCH ==========")
        print(
            f"Job Location: "
            f"{selected_job.get('location')}"
        )
        print(f"Location Match: {location_match}")

        print("\n========================================")

    finally:
        browser.close()


if __name__ == "__main__":
    main()