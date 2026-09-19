from src.matching.role_matcher import RoleMatcher
from src.matching.skill_matcher import SkillMatcher
from src.matching.experience_matcher import ExperienceMatcher
from src.matching.location_matcher import LocationMatcher
from src.matching.job_score import JobScorer


class JobEvaluator:
    """
    Evaluates a job against the candidate's profile
    and job preferences.
    """
    def __init__(self,
                candidate_skills:list,
                target_roles:list,
                preferred_locations:list,
                preferred_work_modes:list,
                candidate_min_experience: int =0 ,
                candidate_max_experience: int=2):
        self.skill_matcher=SkillMatcher(candidate_skills)
        self.role_matcher=RoleMatcher(target_roles)
        self.location_matcher= LocationMatcher(preferred_locations,preferred_work_modes)
        self.experience_matcher= ExperienceMatcher(
            candidate_min_experience,
            candidate_max_experience
        )
        self.job_score=JobScorer()
        self.candidate_skills=candidate_skills

    def evaluate(self,job:dict)->dict:
        """
        Evaluate a single job.
        """
        job_title=job.get("title","")
        job_location=job.get("location","")
        job_experience=job.get("experience","")
        job_skills=job.get("skills","")

        #role_matching
        role_result=self.role_matcher.get_match_result(job_title)

        # Skill Matching
        skill_result= self.skill_matcher.get_match_result(job_skills)

        # Experience Mathching
        experience_result= self.experience_matcher.get_match_result(job_experience)

        #Location Matching
        location_result=self.location_matcher.get_match_result(job_location)


        # Convert boolean matches into percentages
        role_score=100 if role_result["match"] else 0

        experience_score=(100 if experience_result["match"] else 0)

        location_score= (100 if location_result["match"] else 0)

        skill_score= skill_result["match_percentage"]


        # Calculate final score

        final_score= self.job_score.calculate_score(
            role_match=role_score,
            skill_match=skill_score,
            location_match=location_score,
            experience_match=experience_score


        )

        return {
            "job_title": job_title,
            "location": job_location,
            "experience": job_experience,

            "role_match": role_result,

            "skill_match": skill_result,

            "experience_match": experience_result,

            "location_match": location_result,

            "final_score": final_score,

            "score_category": self.job_score.get_score_category(
                final_score
            )
        }
