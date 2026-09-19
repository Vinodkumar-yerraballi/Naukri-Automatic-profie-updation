from src.ingestion.naukri_search import NaukriSearch


def main():

    roles = [
        "Data Analyst",
        "Data Scientist",
        "AI Analyst"
    ]

    locations = [
        "Remote",
        "Bangalore",
        "Hyderabad"
    ]

    work_modes = [
        "Remote",
        "Hybrid"
    ]

    naukri = NaukriSearch(
        roles=roles,
        locations=locations,
        work_modes=work_modes
    )

    print("Source:")
    print(naukri.get_source_name())

    print("\nSearch Queries:")

    jobs = naukri.fetch_jobs()

    for index, job in enumerate(jobs, start=1):

        print(f"\n{index}.")
        print("Role:", job["role"])
        print("Location:", job["location"])
        print("Work Modes:", job["work_mode"])


if __name__ == "__main__":
    main()