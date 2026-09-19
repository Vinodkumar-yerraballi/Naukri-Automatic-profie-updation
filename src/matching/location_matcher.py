class LocationMatcher:
    """
    Matches a job location against the candidate's
    preferred locations and work modes.
    """
    def __init__(self,preferred_locations:list,
                preferred_work_modes:list):
            self.preferred_locations=[
                location.strip().lower() 
                for location in preferred_locations
                ]
            self.preferred_work_modes =[
                work.strip().lower()
                for work in preferred_work_modes
                ]
    def match_location(self,job_location:str)->bool:
        """
        Check whether the job location matches
        a preferred location or work mode.
        """
        if not job_location:
            return False
        job_location=job_location.lower().strip()
        for location in self.preferred_locations:
            if location in job_location:
                return True
        for work_mode in self.preferred_work_modes:
            if work_mode in job_location:
                return True
        return False
    def get_match_result(self,job_location:str)->dict:
        if not job_location:
            return {
                "job_location":job_location,
                "match":None,
                "matched_location":None
            }
        job_location_lower=job_location.strip().lower()
        matched_location=None
        for location in self.preferred_locations:
            if location in job_location_lower:
                matched_location=location
                break
        if matched_location is None:
            for work_mode in self.preferred_work_modes:
                if work_mode in job_location_lower:
                    matched_location=work_mode
                    break
        return {
            "job_location":job_location,
            "match":matched_location is not None,
            "matched_location":matched_location
        }


