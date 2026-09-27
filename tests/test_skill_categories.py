from src.extraction.skill_dictionary import (
    JOB_SKILLS,
    TECHNICAL_SKILLS,
    GENERAL_REQUIREMENTS
)


def main():

    print("\n========== SKILL CATEGORY TEST ==========")

    print(f"Total JOB_SKILLS          : {len(JOB_SKILLS)}")
    print(f"Total TECHNICAL_SKILLS    : {len(TECHNICAL_SKILLS)}")
    print(f"Total GENERAL_REQUIREMENTS: {len(GENERAL_REQUIREMENTS)}")

    print("\n========== GENERAL REQUIREMENTS ==========")

    for skill in GENERAL_REQUIREMENTS:
        print(f"✓ {skill}")

    print("\n========== SAMPLE TECHNICAL SKILLS ==========")

    for skill in TECHNICAL_SKILLS[:20]:
        print(f"✓ {skill}")

    print("\n============================================")


if __name__ == "__main__":
    main()