from src.config.config_manager import ConfigManager

class PermissionManager:
    """
    Checks job eligibility and routes eligible jobs for human review.
    """
    def __init__(self):
        config_manager = ConfigManager()
        self.minimum_score = config_manager.get_minimum_score()
    def check_score(self,score:float)->bool:
        """
        Check whether the job meets the minimum score.
        """
        return score >=self.minimum_score
    def requires_review(self,score:float)-> bool:
        """
        Determine whether the job requires user review.
        """
        return self.check_score(score)
    def get_permission_status(self,score:float)->str:
        """
        Return the current permission status.
        """
        if not self.check_score(score):
            return "REJECTED"
        return "REVIEW"
