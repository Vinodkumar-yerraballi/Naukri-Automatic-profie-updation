import re

from src.extraction.skill_dictionary import JOB_SKILLS


class JDExtractor:

    def __init__(self, job_description: str):
        self.job_description = job_description

    def extract_title(self) -> str:
        lines = self.job_description.splitlines()

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if line.lower() == "job description":
                continue

            return line

        return "Not specified"

    
    def extract_company(self) -> str:
        import re

        patterns = [
            r"^\s*(.+?)\s+is\s+looking\s+for\b",
            r"^\s*(.+?)\s+is\s+hiring\b",
            r"^\s*Company\s*:\s*(.+?)\s*$",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                self.job_description,
                flags=re.IGNORECASE | re.MULTILINE
            )
            if match:
                company = match.group(1).strip()
                if company:
                    return company

        return "Not specified"


    def extract_experience(self) -> str:
        patterns = [
            r"(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\s*to\s*(\d+)\s*(?:years?|yrs?)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                self.job_description,
                re.IGNORECASE
            )

            if match:
                return f"{int(match.group(1))}-{int(match.group(2))} years"

        plus_pattern = r"(\d+)\s*\+\s*(?:years?|yrs?)"

        match = re.search(
            plus_pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return f"{int(match.group(1))}+ years"

        return "Not specified"

    def extract_location(self) -> str:
        pattern = r"Location\s*:\s*(.+)"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_skills(self) -> dict:
        from src.extraction.skill_dictionary import (
            TECHNICAL_SKILLS,
            GENERAL_REQUIREMENTS
        )

        key_technical_skills = []
        description_technical_skills = []

        key_general_requirements = []
        description_general_requirements = []

        jd_lower = self.job_description.lower()

        # ============================================================
        # 1. Extract Naukri Key Skills section
        # ============================================================

        key_skills_text = ""

        key_skills_match = re.search(
            r"Key Skills\s*(.*?)(?=\n\s*(?:Role:|Industry Type:|Department:|Employment Type:|Role Category:|Education|UG:|PG:)|\Z)",
            self.job_description,
            re.IGNORECASE | re.DOTALL
        )

        if key_skills_match:
            key_skills_text = key_skills_match.group(1).strip().lower()

        # ============================================================
        # 2. Remove Key Skills section from normal JD
        # ============================================================

        normal_jd_text = jd_lower

        if key_skills_match:
            normal_jd_text = (
                jd_lower[:key_skills_match.start()]
                + jd_lower[key_skills_match.end():]
            )

        # ============================================================
        # 3. Find technical skills in normal JD
        # ============================================================

        for skill in TECHNICAL_SKILLS:

            skill_clean = skill.strip()

            if not skill_clean:
                continue

            skill_lower = skill_clean.lower()

            if len(skill_lower) <= 2:
                continue

            pattern = rf"(?<!\w){re.escape(skill_lower)}(?!\w)"

            if re.search(pattern, normal_jd_text):
                description_technical_skills.append(skill_clean)

        # ============================================================
        # 4. Find general requirements in normal JD
        # ============================================================

        for requirement in GENERAL_REQUIREMENTS:

            requirement_clean = requirement.strip()

            if not requirement_clean:
                continue

            requirement_lower = requirement_clean.lower()

            if len(requirement_lower) <= 2:
                continue

            pattern = rf"(?<!\w){re.escape(requirement_lower)}(?!\w)"

            if re.search(pattern, normal_jd_text):
                description_general_requirements.append(
                    requirement_clean
                )

        # ============================================================
        # 5. Find technical skills in Naukri Key Skills
        # ============================================================

        if key_skills_text:

            for skill in TECHNICAL_SKILLS:

                skill_clean = skill.strip()

                if not skill_clean:
                    continue

                skill_lower = skill_clean.lower()

                if len(skill_lower) <= 2:
                    continue

                pattern = rf"(?<!\w){re.escape(skill_lower)}(?!\w)"
                if re.search(pattern, key_skills_text):
                    key_technical_skills.append(skill_clean)

        # ============================================================
        # 6. Find general requirements in Naukri Key Skills
        # ============================================================

        if key_skills_text:

            for requirement in GENERAL_REQUIREMENTS:

                requirement_clean = requirement.strip()

                if not requirement_clean:
                    continue

                requirement_lower = requirement_clean.lower()

                if len(requirement_lower) <= 2:
                    continue

                pattern = rf"(?<!\w){re.escape(requirement_lower)}(?!\w)"
                if re.search(pattern, key_skills_text):
                    key_general_requirements.append(
                        requirement_clean
                    )

        key_technical_skills = list(dict.fromkeys(key_technical_skills))
        description_technical_skills = list(
            dict.fromkeys(description_technical_skills)
        )
        key_general_requirements = list(
            dict.fromkeys(key_general_requirements)
        )
        description_general_requirements = list(
            dict.fromkeys(description_general_requirements)
        )
        technical_skills = list(
            dict.fromkeys(
                key_technical_skills + description_technical_skills
            )
        )
        general_requirements = list(
            dict.fromkeys(
                key_general_requirements
                + description_general_requirements
            )
        )

        # ============================================================
        # 8. Return separated results
        # ============================================================

        return {
            "key_technical_skills": key_technical_skills,
            "description_technical_skills": description_technical_skills,

            "technical_skills": technical_skills,

            "key_general_requirements": key_general_requirements,
            "description_general_requirements":
                description_general_requirements,

            "general_requirements": general_requirements
        }

    def extract_all(self) -> dict:

        skill_result = self.extract_skills()

        return {
            "title": self.extract_title(),
            "company": self.extract_company(),
            "location": self.extract_location(),
            "experience": self.extract_experience(),

            "skills": skill_result["technical_skills"],
            "technical_skills": skill_result["technical_skills"],
            "general_requirements":
                skill_result["general_requirements"],

            "job_description": self.job_description
        }