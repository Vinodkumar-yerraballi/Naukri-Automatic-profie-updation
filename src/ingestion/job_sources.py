class JobSource:
    """
    Base class for job Source
    """
    def __init__(self,source_name:str):
        self.source_name=source_name
    def get_source_name(self)->str:
        return self.source_name
    def fetch_jobs(self)->list:
        """
        Fetch jobs from the source.

        This method will be implemented
        by individual job source classes.
        """

        raise NotImplementedError(
            "fetch_jobs() must be implemented by the job source."
        )
