[1mdiff --git a/tests/manual_naukri_pipeline_single_job.py b/tests/manual_naukri_pipeline_single_job.py[m
[1mindex cd99071..3e5cfb0 100644[m
[1m--- a/tests/manual_naukri_pipeline_single_job.py[m
[1m+++ b/tests/manual_naukri_pipeline_single_job.py[m
[36m@@ -3,211 +3,215 @@[m [mfrom src.ingestion.job_collector import JobCollector[m
 from src.matching.job_evaluator import JobEvaluator[m
 from src.database.job_repository import JobRepository[m
 from src.profile.profile_updater import ProfileManager[m
 from src.config.config_manager import ConfigManager[m
 [m
[32m+[m[32mdef main():[m
[32m+[m[32m        print("\n========== NAUKRI SINGLE JOB PIPELINE TEST ==========")[m
 [m
[31m-print("\n========== NAUKRI SINGLE JOB PIPELINE TEST ==========")[m
[32m+[m[32m        config_manager = ConfigManager()[m
 [m
[31m-config_manager = ConfigManager()[m
[32m+[m[32m        profile_manager = ProfileManager([m
[32m+[m[32m            "config/profile.yaml"[m
[32m+[m[32m        )[m
 [m
[31m-profile_manager = ProfileManager([m
[31m-    "config/profile.yaml"[m
[31m-)[m
[32m+[m[32m        profile_manager.load_profile()[m
 [m
[31m-profile_manager.load_profile()[m
[32m+[m[32m        candidate_skills = profile_manager.get_all_skills()[m
[32m+[m[32m        target_roles = profile_manager.get_target_roles()[m
 [m
[31m-candidate_skills = profile_manager.get_all_skills()[m
[31m-target_roles = profile_manager.get_target_roles()[m
[32m+[m[32m        job_search_config = config_manager.get_job_search_config()[m
 [m
[31m-job_search_config = config_manager.get_job_search_config()[m
[32m+[m[32m        preferred_locations = job_search_config.get([m
[32m+[m[32m            "locations",[m
[32m+[m[32m            [][m
[32m+[m[32m        )[m
 [m
[31m-preferred_locations = job_search_config.get([m
[31m-    "locations",[m
[31m-    [][m
[31m-)[m
[32m+[m[32m        preferred_work_modes = job_search_config.get([m
[32m+[m[32m            "work_modes",[m
[32m+[m[32m            [][m
[32m+[m[32m        )[m
 [m
[31m-preferred_work_modes = job_search_config.get([m
[31m-    "work_modes",[m
[31m-    [][m
[31m-)[m
[32m+[m[32m        experience_config = job_search_config.get([m
[32m+[m[32m            "experience",[m
[32m+[m[32m            {}[m
[32m+[m[32m        )[m
 [m
[31m-experience_config = job_search_config.get([m
[31m-    "experience",[m
[31m-    {}[m
[31m-)[m
[32m+[m[32m        candidate_min_experience = experience_config.get([m
[32m+[m[32m            "minimum",[m
[32m+[m[32m            0[m
[32m+[m[32m        )[m
 [m
[31m-candidate_min_experience = experience_config.get([m
[31m-    "minimum",[m
[31m-    0[m
[31m-)[m
[32m+[m[32m        candidate_max_experience = experience_config.get([m
[32m+[m[32m            "maximum",[m
[32m+[m[32m            2[m
[32m+[m[32m        )[m
 [m
[31m-candidate_max_experience = experience_config.get([m
[31m-    "maximum",[m
[31m-    2[m
[31m-)[m
 [m
[32m+[m[32m        evaluator = JobEvaluator([m
[32m+[m[32m            candidate_skills=candidate_skills,[m
[32m+[m[32m            target_roles=target_roles,[m
[32m+[m[32m            preferred_locations=preferred_locations,[m
[32m+[m[32m            preferred_work_modes=preferred_work_modes,[m
[32m+[m[32m            candidate_min_experience=candidate_min_experience,[m
[32m+[m[32m            candidate_max_experience=candidate_max_experience[m
[32m+[m[32m        )[m
 [m
[31m-evaluator = JobEvaluator([m
[31m-    candidate_skills=candidate_skills,[m
[31m-    target_roles=target_roles,[m
[31m-    preferred_locations=preferred_locations,[m
[31m-    preferred_work_modes=preferred_work_modes,[m
[31m-    candidate_min_experience=candidate_min_experience,[m
[31m-    candidate_max_experience=candidate_max_experience[m
[31m-)[m
[32m+[m[32m        repository = JobRepository()[m
 [m
[31m-repository = JobRepository()[m
[32m+[m[32m        collector = JobCollector([m
[32m+[m[32m            evaluator=evaluator,[m
[32m+[m[32m            repository=repository[m
[32m+[m[32m        )[m
 [m
[31m-collector = JobCollector([m
[31m-    evaluator=evaluator,[m
[31m-    repository=repository[m
[31m-)[m
[32m+[m[32m        browser = NaukriBrowser()[m
 [m
[31m-browser = NaukriBrowser()[m
[32m+[m[32m        try:[m
 [m
[31m-try:[m
[32m+[m[32m            browser.start()[m
 [m
[31m-    browser.start()[m
[32m+[m[32m            browser.search_jobs([m
[32m+[m[32m                role="Data Analyst",[m
[32m+[m[32m                location="Remote"[m
[32m+[m[32m            )[m
 [m
[31m-    browser.search_jobs([m
[31m-        role="Data Analyst",[m
[31m-        location="Remote"[m
[31m-    )[m
[32m+[m[32m            jobs = browser.get_job_cards()[m
 [m
[31m-    jobs = browser.get_job_cards()[m
[32m+[m[32m            print(f"\nJobs found: {len(jobs)}")[m
 [m
[31m-    print(f"\nJobs found: {len(jobs)}")[m
[32m+[m[32m            if not jobs:[m
[32m+[m[32m                print("No jobs found.")[m
[32m+[m[32m            else:[m
 [m
[31m-    if not jobs:[m
[31m-        print("No jobs found.")[m
[31m-    else:[m
[32m+[m[32m                # Process only one job[m
[32m+[m[32m                job = jobs[1][m
 [m
[31m-        # Process only one job[m
[31m-        job = jobs[1][m
[32m+[m[32m                print("\n========== SELECTED JOB ==========")[m
 [m
[31m-        print("\n========== SELECTED JOB ==========")[m
[32m+[m[32m                print(f"Title:      {job.get('title')}")[m
[32m+[m[32m                print(f"Company:    {job.get('company')}")[m
[32m+[m[32m                print(f"Location:   {job.get('location')}")[m
[32m+[m[32m                print(f"Experience: {job.get('experience')}")[m
[32m+[m[32m                print(f"URL:        {job.get('job_url')}")[m
 [m
[31m-        print(f"Title:      {job.get('title')}")[m
[31m-        print(f"Company:    {job.get('company')}")[m
[31m-        print(f"Location:   {job.get('location')}")[m
[31m-        print(f"Experience: {job.get('experience')}")[m
[31m-        print(f"URL:        {job.get('job_url')}")[m
[32m+[m[32m                print("\n========== EXTRACTING DETAILS ==========")[m
 [m
[31m-        print("\n========== EXTRACTING DETAILS ==========")[m
[32m+[m[32m                job = browser.extract_job_details(job)[m
 [m
[31m-        job = browser.extract_job_details(job)[m
[32m+[m[32m                if job.get("security_challenge"):[m
[32m+[m[32m                    print("\nSecurity challenge detected.")[m
[32m+[m[32m                    print("Manual action is required.")[m
 [m
[31m-        if job.get("security_challenge"):[m
[31m-            print("\nSecurity challenge detected.")[m
[31m-            print("Manual action is required.")[m
[32m+[m[32m                else:[m
 [m
[31m-        else:[m
[32m+[m[32m                    job_description = job.get([m
[32m+[m[32m                        "job_description",[m
[32m+[m[32m                        ""[m
[32m+[m[32m                    )[m
 [m
[31m-            job_description = job.get([m
[31m-                "job_description",[m
[31m-                ""[m
[31m-            )[m
[32m+[m[32m                    print([m
[32m+[m[32m                        f"\nJob description length: "[m
[32m+[m[32m                        f"{len(job_description)}"[m
[32m+[m[32m                    )[m
 [m
[31m-            print([m
[31m-                f"\nJob description length: "[m
[31m-                f"{len(job_description)}"[m
[31m-            )[m
[32m+[m[32m                    if not job_description.strip():[m
 [m
[31m-            if not job_description.strip():[m
[32m+[m[32m                        print([m
[32m+[m[32m                            "\nJob description is empty."[m
[32m+[m[32m                        )[m
 [m
[31m-                print([m
[31m-                    