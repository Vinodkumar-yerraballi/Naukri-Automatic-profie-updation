class SkillMatcher:

    """"
    Compares the candidate's skills with the skills
    required or mentioned in a job description.
    """
    def __init__(self,candidate_skills:list):
        self.candidate_skills={
            skill.strip().lower()
            for skill in candidate_skills
        }

    def find_matched_skills(self,job_skills:list)->list:
        """"
        Return the both skills matched in the jd and candidate resume
        """
        matched_skills=[]
        for skill in job_skills:
            if skill.strip().lower() in self.candidate_skills:
                matched_skills.append(skill)
        return matched_skills
    def finding_missing_skills(self,job_skills:list)->list:
        """
        Return the job skills that not in the candidate profile
        """
        missing_skills=[]
        for skills in job_skills:
            if skills.strip().lower() not in self.candidate_skills:
                missing_skills.append(skills)
        return missing_skills
    def calculate_match_percentage(self,job_skills:list)->float:
        """
        Calculate the percentage of job skills
        that match the candidate's skills.
        """
        if not job_skills:
            return 0.0
        matched_skills=self.find_matched_skills(job_skills)
        percentage=(len(matched_skills)/len(job_skills))*100
        return round(percentage,2)

    def get_match_result(self,job_skills:list)->dict:
        """
        Return a complete skill matching result.
        """
        matched=self.find_matched_skills(job_skills)
        missing=self.finding_missing_skills(job_skills)
        percentage=self.calculate_match_percentage(job_skills)


        return {
            "matched_skills":matched,
            "missing_skills":missing,
            "match_percentage": percentage
        }

