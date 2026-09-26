import re
from src.extraction.skill_dictionary import JOB_SKILLS


class JDExtractor:

    def __init__(self, job_description: str):
        self.job_description = job_description

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

    def extract_skills(self) -> list:
        """
        Extract skills from the job description.

        Normal JD text:
            Uses strict whole-word matching.

        Naukri Key Skills section:
            Naukri sometimes concatenates skills together, for example:

            project managementdata analyticsoracledata analysis
            data managementsqldata cleansingexceldata qualitytableauspark

            Therefore, the Key Skills section is handled separately.
        """

        found_skills = []

        jd_lower = self.job_description.lower()

        # ---------------------------------------------------------
        # 1. Extract the Naukri "Key Skills" section
        # ---------------------------------------------------------

        key_skills_text = ""

        key_skills_match = re.search(
            r"Key Skills\s*(.*?)(?=\n\s*$|\Z)",
            self.job_description,
            re.IGNORECASE | re.DOTALL
        )

        if key_skills_match:
            key_skills_text = key_skills_match.group(1).strip().lower()

        # ---------------------------------------------------------
        # 2. Remove Key Skills section from normal JD text
        # ---------------------------------------------------------

        normal_jd_text = jd_lower

        if key_skills_match:
            normal_jd_text = (
                jd_lower[:key_skills_match.start()]
                + jd_lower[key_skills_match.end():]
            )

        # ---------------------------------------------------------
        # 3. Check skills in normal JD text
        # ---------------------------------------------------------

        for skill in JOB_SKILLS:

            skill_clean = skill.strip()

            if not skill_clean:
                continue

            skill_lower = skill_clean.lower()

            # Special handling for single-character skills
            # such as "R".
            if len(skill_lower) == 1:
                if skill_lower == "r":
                    pattern = r"(?<![\w+#])r(?![\w+#])"

                    if re.search(pattern, normal_jd_text):
                        found_skills.append(skill_clean)

                continue

            escaped_skill = re.escape(skill_lower)

            pattern = rf"(?<!\w){escaped_skill}(?!\w)"

            if re.search(pattern, normal_jd_text):
                found_skills.append(skill_clean)

        # ---------------------------------------------------------
        # 4. Check skills inside Naukri Key Skills section
        # ---------------------------------------------------------

        if key_skills_text:

            for skill in JOB_SKILLS:

                skill_clean = skill.strip()

                if not skill_clean:
                    continue

                skill_lower = skill_clean.lower()

                # Do NOT search single-character skills such as R
                # inside concatenated Key Skills text.
                #
                # Example:
                # "data analytics" contains many letter "r"s,
                # but that does NOT mean the job requires R.
                if len(skill_lower) == 1:
                    continue

                if skill_lower in key_skills_text:
                    found_skills.append(skill_clean)

        # ---------------------------------------------------------
        # 5. Remove duplicate skills while preserving order
        # ---------------------------------------------------------

        unique_skills = []

        for skill in found_skills:
            if skill not in unique_skills:
                unique_skills.append(skill)

        return unique_skills

    def extract_title(self) -> str:

        lines = [
            line.strip()
            for line in self.job_description.splitlines()
            if line.strip()
        ]

        if not lines:
            return "Not specified"

        ignored_titles = {
            "job description",
            "job details",
            "description",
            "about the job",
            "role description"
        }

        for line in lines:

            if line.lower() not in ignored_titles:
                return line

        return "Not specified"

    def extract_company(self) -> str:

        pattern = r"([A-Za-z0-9&., ]+)\s+is\s+looking\s+for"

        match = re.search(
            pattern,
            self.job_description,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return "Not specified"

    def extract_all(self) -> dict:

        return {
            "title": self.extract_title(),
            "company": self.extract_company(),
            "location": self.extract_location(),
            "experience": self.extract_experience(),
            "skills": self.extract_skills(),
            "job_description": self.job_description
        }