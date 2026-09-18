from pathlib import Path
import yaml


class ProfileManager:
    "Load the update the candiate profile"
    def __init__(self, profile_path: str):
        self.profile_path = Path(profile_path)
        self.profile= None

    def load_profile(self):
        "Load candidate profile from yaml file"
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile file not found: {self.profile_path}")

        with open(self.profile_path,'r',encoding='utf-8') as file:
            self.profile = yaml.safe_load(file)
        if not self.profile:
            raise ValueError(f"Profile file is empty")
        return self.profile
    def get_candidate_name(self)->str:
        "Get the candidate name"
        if self.profile is None:
            self.load_profile()
        return self.profile["candidate"]["name"]
    def get_target_roles(self):
        "Get the target roles"
        if self.profile is None:
            self.load_profile()
        return self.profile.get("target_roles", [])
    def get_all_skills(self):
        "Get all the skills from the profile"
        if self.profile is None:
            self.load_profile()
        skills=[]
        skills_category=self.profile.get("skills",{})
        for category in skills_category.values():
            skills.extend(category)
        return skills