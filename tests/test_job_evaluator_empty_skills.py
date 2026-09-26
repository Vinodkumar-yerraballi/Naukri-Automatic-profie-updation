from src.matching.job_evaluator import JobEvaluator


candidate_skills = [
    "Python",
    "SQL",
    "Power BI"
]

target_roles = [
    "Data Analyst"
]

preferred_locations = [
    "Remote"
]

preferred_work_modes = [
    "Remote"
]


evaluator = JobEvaluator(
    candidate_skills=candidate_skills,
    target_roles=target_roles,
    preferred_locations=preferred_locations,
    preferred_work_modes=preferred_work_modes,
    candidate_min_experience=0,
    candidate_max_experience=2
)


job = {
    "title": "Data Analyst",
    "location": "Remote",
    "experience": "0-2 years",
    "skills": []
}


result = evaluator.evaluate(job)


print("\n========== EMPTY SKILL EVALUATION TEST ==========")

print("\nJob:")
print(job)

print("\nMatched skills:")
print(result["skill_match"]["matched_skills"])

print("\nMissing skills:")
print(result["skill_match"]["missing_skills"])

print("\nSkill match percentage:")
print(result["skill_match"]["match_percentage"])

print("\nRole match:")
print(result["role_match"])

print("\nExperience match:")
print(result["experience_match"])

print("\nLocation match:")
print(result["location_match"])

print("\nFinal score:")
print(result["final_score"])

print("\nScore category:")
print(result["score_category"])

print("\n========== TEST COMPLETED ==========")