mkdir -p config
touch  config/config.yaml
touch  config/profile.yaml
touch  config/job_preferences.yaml

mkdir -p data
mkdir -p data/raw
mkdir -p data/processed

mkdir -p src
mkdir -p src/ingestion
touch  src/ingestion/__init__.py
touch  src/ingestion/naukri_search.py
touch  src/ingestion/job_sources.py

mkdir -p src/config
touch src/config/__init__.py
touch src/config/config_manger.py

mkdir -p src/pipelines
touch scr/pipelines/__init__.py
touch src/pipelines/job_pipeline.py

mkdir -p src/extraction
touch  src/extraction/__init__.py
touch  src/extraction/jb_extractor.py
touch  src/extraction/resume_parser.py

mkdir -p src/matching
touch  src/matching/__init__.py
touch  src/matching/skill_matcher.py
touch  src/matching/experience_matcher.py
touch  src/matching/job_score.py

mkdir -p src/application
touch  src/application/__init__.py
touch  src/application/apply_engine.py
touch  src/application/permission.py
touch  src/application/captch_solver.py


mkdir -p src/profile
touch  src/profile/__init__.py
touch  src/profile/profile_updater.py

mkdir -p src/database
touch  src/database/__init__.py
touch  src/database/db.py

mkdir -p src/notification
touch  src/notification/__init__.py
touch  src/notification/notifier.py

mkdir -p src/utils
touch  src/utils/__init__.py
touch  src/utils/logger.py
touch  src/utils/helper.py

touch  requirements.txt
touch  main.py
touch  .env

