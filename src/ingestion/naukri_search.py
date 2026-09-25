from src.ingestion.job_sources import JobSource
from src.config.config_manager import ConfigManager

class NaukriSearch(JobSource):
    """
    Handles job search configuration for Naukri.
    """
    def __init__(self):
        super().__init__("Naukri")
        config_manger=ConfigManager()
        job_search_config=config_manger.get_job_search_config()
        self.roles=job_search_config.get("roles",[])
        self.locations=job_search_config.get("locations",[])
        self.work_modes=job_search_config.get("work_modes",[])
        self.experience=job_search_config.get("experience",[])
        self.employment_type=job_search_config.get("employment_type",[])
    def build_search_queries(self)->list:
        """
        Build search combinations from roles and locations.
        """
        queries=[]
        for role in self.roles:
            for location in self.locations:
                query={
                    "role": role,
                    "location": location,
                    "work_mode": self.work_modes,
                    "experience": self.experience,
                    "employment_type": self.employment_type

                }
                queries.append(query)
        return queries

    def fetch_jobs(self)->list:
        """
        Return search configurations.

        Actual website collection will be added
        after the search configuration is tested.
        """
        return self.build_search_queries()