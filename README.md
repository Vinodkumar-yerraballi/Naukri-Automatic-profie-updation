# Job Pipeline and Resume Updates

Find recent Naukri listings that fit your goals, compare them with your
candidate profile, and prepare job-specific resume drafts for your review. The
project can also upload a changed source resume to signed-in Naukri, Foundit,
and Indeed profiles.

This is a **review-first** job assistant. It requires your terminal approval
for each job before attempting a supported one-step Naukri application. It
can add resume-supported skills, work experience, and projects to Foundit.
Other profile fields are not automatically changed. Wellfound resume changes
are not automated.

> A stronger profile comes from clear, truthful evidence of your work. This
> tool can help organize that evidence and target relevant roles, but it cannot
> guarantee interviews or job offers.

## What it does

1. Searches Naukri for the configured roles and locations.
2. Filters out listings outside the configured posting-age window.
3. Scores jobs against your skills, experience, location, education, and
   preferences.
4. Combines skills found in Naukri's key-skills list and the full job
   description, and skips descriptions that contain recognized page-interface
   text.
5. Stores matching jobs locally and lets you review the queue.
6. Can generate a separate DOCX resume draft for a suitable job.
7. Can upload your changed source PDF to your signed-in Naukri, Foundit, and
   Indeed profiles, and add resume-supported skills, experience, and projects
   to Foundit.
8. Can prepare a Naukri profile-update proposal as JSON for you to review and
   apply manually.
9. With `application.auto_apply: true`, can attempt a supported one-step
   application after you approve that specific job in the terminal.

## Project structure

```text
.
|-- main.py                         # Command-line entry point
|-- requirements.txt                # Python dependencies
|-- HOW_TO_RUN.txt                  # General Windows run instructions
|-- HOW_TO_RUN_NAUKRI.txt           # Naukri resume/profile instructions
|-- HOW_TO_RUN_FOUNDIT.txt          # Foundit resume/profile instructions
|-- HOW_TO_RUN_INDEED.txt           # Indeed resume instructions
|-- HOW_TO_RUN_WELLFOUND.txt        # Wellfound manual resume instructions
|-- config/
|   |-- config.yaml                 # General paths, database, and logging
|   |-- profile.yaml                # Candidate skills, education, and roles
|   `-- job_preferences.yaml        # Search, scoring, AI, and schedule options
|-- src/
|   |-- application/                 # Review queue, tracker, permissions
|   |-- config/                      # YAML configuration loading
|   |-- database/                    # Local database and job repository
|   |-- extraction/                  # Resume and job-description parsing
|   |-- ingestion/                   # Naukri browser and job collection
|   |-- matching/                    # Role, skill, location, and score logic
|   |-- notification/                # Notifications
|   |-- pipelines/                   # Job pipeline and daily scheduler
|   |-- profile/                     # Resume upload, tailoring, proposals
|   `-- utils/                       # Shared helpers and logging
|-- tests/                           # Automated tests
`-- data/                            # Local databases, browser session, files
    |-- raw/                          # Raw input data
    `-- processed/                    # Generated proposals and resume drafts
```

Generated files and private data belong under `data/`; do not commit your
resume, login session, API keys, or generated drafts.

## Requirements and release status

- Windows 10/11 or another operating system that can run Python and Chromium.
- Python **3.10 or newer**.
- A Naukri account for browsing and optional resume upload.
- An AI provider for resume tailoring (Gemini, Ollama, or Anthropic).

The runtime dependencies are listed in `requirements.txt`:

| Package | Purpose |
| --- | --- |
| `PyYAML` | Read project configuration |
| `python-dotenv` | Load local API keys from `.env` |
| `playwright` | Control Chromium for Naukri browsing |
| `pypdf` | Extract text from PDF resumes |
| `python-docx` | Create tailored DOCX drafts |
| `tzdata` | Provide time-zone data where the operating system needs it |

The dependency file currently does not pin exact package versions. For
repeatable environments, use a virtual environment and retain the installed
versions you have tested.

The configuration declares application version `1.0.0` in
`config/config.yaml`. This repository currently provides the application as
source code; it does not define a pip-installable package or publish a
downloadable release. Clone or download the repository, then install its
dependencies as described below.

## Set it up on your personal laptop

### 1. Get the project and open PowerShell

Open PowerShell in the project folder. For example:

```powershell
cd "C:\Users\<your-name>\Projects\Naukri-Automatic-profie-updation"
```

Use your actual project folder path in place of the example.

### 2. Create a virtual environment and install dependencies

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

If the Python launcher is unavailable, install Python 3.10+ and use
`python -m venv .venv` in the first command.

### 3. Add your source resume

Save a **text-based** PDF as `data\resume.pdf`. A scanned/image-only PDF may
not contain extractable text, so the matching and tailoring features may not
work correctly. The parser also supports other formats; if you use a different
file or location, update `resume_path` under `resume_tailoring` in
`config\job_preferences.yaml`. If Naukri resume upload is enabled, also set
`naukri_profile.resume_path` in that file.

Keep this file as your accurate, general-purpose source resume. Generated
job-specific drafts go into `data\processed\resumes` and must not replace the
source file.

### 4. Configure your candidate profile and job preferences

Edit:

- `config\profile.yaml`: skills, education, and target roles.
- `config\job_preferences.yaml`: search roles and locations, experience,
  match threshold, AI provider, resume paths, and schedule.

Use skills and experience you can support with real examples. For stronger
matching, use recognizable skill names and keep your configured roles and
locations focused on jobs you would genuinely consider.

### 5. Configure resume-tailoring AI

The default configuration uses Gemini first and Ollama as a local fallback.
Choose one of these setups:

**Gemini with local Ollama fallback**

1. Create an API key using [Google AI Studio](https://aistudio.google.com/apikey).
2. Create a `.env` file in the project root containing:

   ```text
   GEMINI_API_KEY=your_key_here
   ```

3. Install [Ollama](https://ollama.com/download), then download the configured
   fallback model:

   ```powershell
   ollama pull qwen3:8b
   ```

   Keep Ollama running when you use it as a fallback.

Resume text and job descriptions are sent to the selected cloud AI when using
Gemini or Anthropic. Review the provider's current privacy, data-use, pricing,
and model-availability terms before sending personal information. Ollama
processes requests locally on your computer.

**Ollama only**

Set `provider: ollama` and `model: qwen3:8b` under `resume_tailoring` in
`config\job_preferences.yaml`. Remove or comment out the
`fallback_provider` setting if you do not want a second provider.

**Anthropic**

Set `provider: anthropic` in `config\job_preferences.yaml` and configure
`ANTHROPIC_API_KEY` in your Windows user environment. Keep API keys out of
source files and chat messages.

### 6. Sign in locally (recommended for resume upload)

The app does not need your Naukri password. It opens a local browser so you can
sign in yourself and save a browser session:

```powershell
.\.venv\Scripts\python.exe main.py --setup-naukri-session
```

Complete any login verification in the browser, return to PowerShell, and
press Enter. The browser session is kept under
`data\naukri_browser_profile`. Treat that folder as sensitive: anyone who can
access it may be able to use the saved session.

Foundit and Indeed use separate local sessions. Sign in yourself in each
opened browser; do not put account passwords in project files:

```powershell
.\.venv\Scripts\python.exe main.py --setup-foundit-session
.\.venv\Scripts\python.exe main.py --setup-indeed-session
```

Each saved browser profile is stored under `data\foundit_browser_profile` or
`data\indeed_browser_profile`. These directories are sensitive. Indeed may
redirect to a region-specific sign-in or require additional verification.

## Run the pipeline

### Run once now

```powershell
.\.venv\Scripts\python.exe main.py
```

The app searches jobs and may prompt you to review matching listings in the
terminal. Keep the terminal open and available for input during an interactive
run.

To update Foundit only, without running a Naukri search:

```powershell
.\.venv\Scripts\python.exe main.py --update-foundit-profile
```

### Run every day

```powershell
.\.venv\Scripts\python.exe main.py --schedule
```

The default schedule is 09:00 in `Asia/Kolkata`, configured in
`config\job_preferences.yaml`. The scheduler waits for the next scheduled
time; it does not run an immediate scan on startup. Keep the laptop awake,
connected to the internet, and the PowerShell window open. For automatic
startup after you sign in to Windows, configure Windows Task Scheduler to run
this command.

### Prepare a profile proposal without searching for jobs

```powershell
.\.venv\Scripts\python.exe main.py --prepare-profile-update
```

The proposal is written to
`data\processed\profile_update_proposal.json`. Review every suggested detail
and make any profile changes yourself. The command does not edit Naukri
profile fields.

## What happens during a run

- If `naukri_profile.update_resume` is enabled, the app compares the source
  resume with the last confirmed upload. It attempts to upload only when the
  file has changed. Login expiry, verification, or upload-confirmation problems
  require manual attention.
- Foundit and Indeed are also enabled for changed-resume upload in
  `config\job_preferences.yaml`. Each platform has its own saved session and
  upload-state file. An upload is recorded only after the site displays a
  recognized success message; if the site's page changes or does not confirm
  the upload, check it manually and retry. The upload automation does not
  bypass login, CAPTCHA, or verification.
- Foundit can add missing resume-supported skills, employment entries, and
  projects. It preserves existing entries rather than replacing them. Profile
  fields are processed once per resume version using the configured AI
  provider. Indeed currently supports resume upload only.
- Wellfound is not automatically updated. Its resume workflow may be tied to a
  specific application; attach and verify your resume there yourself.
- Naukri profile fields are not automatically changed; the profile proposal
  is for manual review.
- The job search rotates through configured role/location combinations. The
  defaults search up to eight combinations per run and favor listings posted
  within the last 24 hours.
- Keep the scheduled run attached to an interactive PowerShell window so you
  can review and approve individual jobs. `auto_apply: true` does not skip
  this approval.
- Job skill matching uses both Naukri's key-skills list and skill terms found
  in the description. Recognized page-interface contamination is reported and
  the affected listing is skipped rather than scored from unreliable text.
- Matching listings are stored in the local database and can be reviewed.
  Each job must be approved individually in the interactive terminal queue.
- With `application.auto_apply: true`, an approved job can be submitted using
  Naukri's single, clearly identified **Apply** or **Apply now** action. The
  app does not fill multi-step forms, apply on external sites, or bypass
  login/CAPTCHA/OTP checks. If submission cannot be confirmed, it stops and
  asks you to check Naukri before retrying. Set `auto_apply: false` to record
  approvals without attempting submission. The tailored DOCX is not
  automatically attached; Naukri uses the resume already on your profile.
  The configured daily limit counts confirmed and uncertain attempts.
- `matching.minimum_score` is this project's job-relevance score, not a
  universal ATS score. No ATS percentage (including 90%) can be guaranteed.
- Where a job description is available and the job meets the configured
  criteria, a job-specific resume draft can be saved as a DOCX under
  `data\processed\resumes`.
- Naukri may show CAPTCHA, OTP, or other security checks. Complete these
  yourself in the browser; the app does not bypass them.

## A practical review process for stronger applications

1. **Keep the source resume evidence-based.** Use accurate job titles, dates,
   tools, responsibilities, and outcomes. Never add a skill or achievement
   solely because it appears in a job description.
2. **Tune the profile to your real targets.** Keep the roles, locations,
   experience range, and skills in the YAML files aligned with the work you
   want and can discuss.
3. **Review the match, not just the score.** Open each job listing and check
   its responsibilities, required experience, location, and legitimacy before
   deciding whether it is relevant.
4. **Inspect each generated draft.** Compare it with your source resume and the
   job description. Correct errors, remove unsupported claims, and make sure
   the final resume still sounds like you. Do not submit an AI draft without
   reviewing it.
5. **Prepare interview examples from real work.** For each important project
   or achievement, write down the problem, your contribution, tools used,
   decisions made, result, and what you learned. Be ready to explain tradeoffs
   and limitations, not only list technologies.
6. **Strengthen project descriptions with verifiable detail.** If appropriate,
   include a clear README, setup instructions, screenshots or sample outputs,
   tests, and a short explanation of your own contribution. Do not claim
   production impact or metrics you did not measure.
7. **Approve each application carefully.** Check the role, employer, job
   description, and generated resume draft before approving it in the
   interactive queue. If Naukri presents a multi-step or external application,
   complete it yourself and verify the final status on Naukri.

## Privacy and safe handling

- Never commit `.env`, API keys, passwords, personal resumes, generated drafts,
  or any saved browser session.
- The `.gitignore` excludes the local resume, browser session, upload state,
  generated drafts, and profile proposal.
- Review cloud AI data-use terms before sending resume or job-description
  content to a provider.
- Back up important personal files separately; local databases and generated
  outputs are application data, not a secure cloud backup.

## Tests

The `tests/` folder contains automated tests as well as manual browser
diagnostics. Some `test_naukri_*.py` files open a real browser and access
Naukri, so inspect a test file before running it. Run a specific automated
test module from the project root, for example:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_resume_tailoring.py
```
