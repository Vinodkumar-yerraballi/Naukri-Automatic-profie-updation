from src.ingestion.job_sources import JobSource

class NaukriSearch(JobSource):
    """
    Handles job search configuration for Naukri.
    """
    def __init__(self,
                roles:list,
                locations:list,
                work_modes:list):
        super().__init__("Naukri")
        self.roles=roles
        self.locations=locations
        self.work_modes=work_modes
    def build_search_queries(self)->list:
        """
        Build search combinations from roles and locations.
        """
        queries=[]
        for role in self.roles:
            for location in self.locations:
                query={
                    "role":role,
                    "location":location,
                    "work_mode":self.work_modes

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