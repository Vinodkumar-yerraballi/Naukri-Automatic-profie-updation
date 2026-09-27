from src.profile.profile_updater import ProfileManager


def main():

    profile = ProfileManager("config/profile.yaml")

    profile.load_profile()

    candidate_skills = profile.get_all_skills()

    print("\n========== CANDIDATE SKILLS ==========")

    for skill in candidate_skills:
        print(f"✓ {skill}")

    print(f"\nTotal candidate skills: {len(candidate_skills)}")
    print("=======================================")


if __name__ == "__main__":
    main()