class PermissionManager:
    """
    Controls whether a job is allowed to proceed
    to the application stage.
    """
    def __init__(self,
                minimum_score:float=85.0,
                auto_apply:bool=False):
        self.minimum_score=minimum_score
        self.auto_apply=auto_apply
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


