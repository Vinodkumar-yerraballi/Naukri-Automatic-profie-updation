class LocationMatcher:

    LOCATION_ALIASES = {
        "bangalore": [
            "bangalore",
            "bengaluru"
        ],

        "bengaluru": [
            "bangalore",
            "bengaluru"
        ],

        "hyderabad": [
            "hyderabad"
        ],

        "chennai": [
            "chennai",
            "madras"
        ],

        "remote": [
            "remote",
            "work from home",
            "wfh"
        ]
    }

    def __init__(
        self,
        preferred_locations: list,
        preferred_work_modes: list
    ):

        self.preferred_locations = [
            location.strip().lower()
            for location in preferred_locations
        ]

        self.preferred_work_modes = [
            work.strip().lower()
            for work in preferred_work_modes
        ]

    def match_location(
        self,
        job_location: str
    ) -> bool:

        result = self.get_match_result(
            job_location
        )

        return result["match"]

    def get_match_result(
        self,
        job_location: str
    ) -> dict:

        if not job_location:

            return {
                "job_location": job_location,
                "match": False,
                "matched_location": None
            }

        job_location_lower = (
            job_location.strip().lower()
        )

        # -----------------------------------------
        # Check preferred locations
        # -----------------------------------------

        for preferred in self.preferred_locations:

            aliases = self.LOCATION_ALIASES.get(
                preferred,
                [preferred]
            )

            for alias in aliases:

                if alias in job_location_lower:

                    return {
                        "job_location": job_location,
                        "match": True,
                        "matched_location": preferred
                    }

        # -----------------------------------------
        # Check work modes
        # -----------------------------------------

        for work_mode in self.preferred_work_modes:

            work_mode_lower = (
                work_mode.strip().lower()
            )

            if work_mode_lower in job_location_lower:

                return {
                    "job_location": job_location,
                    "match": True,
                    "matched_location": work_mode
                }

        return {
            "job_location": job_location,
            "match": False,
            "matched_location": None
        }