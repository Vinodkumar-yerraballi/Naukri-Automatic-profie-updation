from src.config.config_manager import ConfigManager

class PermissionManager:
    """
    Controls whether a job is allowed to proceed
    to the application stage.
    """
    def __init__(self):
        config_manger=ConfigManager()
        self.minimum_score=(config_manger.get_minimum_score())
        application_config=(config_manger.get_application_config())
        self.auto_apply=application_config.get(
            "auto_apply",False
        )
        self.application_mode=application_config.get(
            "mode","review"
        )
        self.maximum_applications_per_day=application_config.get(
            "maximum_applications_per_day",15
        )
    def check_score(self,score:float)->bool:
        """
        Check whether the job meets the minimum score.
        """
        return score >=self.minimum_score
    def requires_review(self,score:float)-> bool:
        """
        Determine whether the job requires user review.
        """
        if not self.check_score(score):
            return False
        return not self.auto_apply
    def get_permission_status(self,score:float)->str:
        """
        Return the current permission status.
        """
        if not self.check_score(score):
            return "REJECTED"
        if self.auto_apply:
            return "APPROVE"
        return "REVIEW"


