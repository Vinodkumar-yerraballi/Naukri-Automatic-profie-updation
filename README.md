# Job Pipeline and Resume Updates

Find recent Naukri and Shine listings or run an opt-in Instahyre search,
compare jobs with your candidate profile, and prepare job-specific resume
drafts for your review. Daily AI-generated headline and About proposals can be created for
each configured platform and reviewed before you post them. The project can
also upload a changed source resume to signed-in
Naukri, Foundit, Indeed, Shine, Hirist, and Wellfound profiles.

This is a **review-first** job assistant. It requires your terminal approval
for each job before attempting a supported one-step Naukri application.
Profile-field proposals are saved for review; supported field edits require
you to type `APPLY`. Naukri supports its resume headline and key skills and
adding resume-supported projects. Foundit supports skills, work experience,
and projects. Shine supports its summary, skills, and selected work details.
Indeed, Hirist, and Wellfound currently support resume uploads only. Naukri
remains the default job search; Instahyre and Shine searches are started
separately and never submit applications.

> A stronger profile comes from clear, truthful evidence of your work. This
> tool can help organize that evidence and target relevant roles, but it cannot
> guarantee interviews or job offers.

## What it does

1. Searches Naukri for the configured roles and locations, or runs the
   standalone `--search-instahyre` and `--search-shine` commands.
2. Filters out listings outside the configured posting-age window.
3. Scores jobs against your skills, experience, location, education, and
   preferences.
4. Combines skills found in Naukri's key-skills list and the full job
   description, and skips descriptions that contain recognized page-interface
   text.
5. Stores matching jobs locally and lets you review the queue.
6. Can generate separate DOCX and plain-text resume drafts for a suitable
   job.
7. Can upload your changed source resume to your signed-in Naukri, Foundit,
   Indeed, Shine, Hirist, and Wellfound profiles, and update the supported
   Naukri, Foundit, and Shine profile fields described below.
8. Saves profile-field proposals for review and requires explicit terminal
   confirmation before changing supported profile fields.
9. Can generate one distinct, resume-grounded headline and About proposal per
   platform per day, retaining history and never posting the text automatically.
10. With `application.auto_apply: true`, can attempt a supported one-step
   application after you approve that specific job in the terminal.

## Project structure

```text
.
|-- main.py                         # Command-line entry point
|-- requirements.txt                # Python dependencies
|-- HOW_TO_RUN.txt                  # General Windows run instructions
|-- HOW_TO_RUN_NAUKRI.txt           # Naukri resume/profile instructions
|-- HOW_TO_RUN_INSTAHYRE.txt        # Instahyre search instructions
|-- HOW_TO_RUN_PROFILE_TEXT.txt     # Daily per-platform headline/About prompts
|-- HOW_TO_RUN_FOUNDIT.txt          # Foundit resume/profile instructions
|-- HOW_TO_RUN_INDEED.txt           # Indeed resume instructions
|-- HOW_TO_RUN_SHINE.txt            # Shine resume instructions
|-- HOW_TO_RUN_HIRIST.txt           # Hirist resume instructions
|-- HOW_TO_RUN_WELLFOUND.txt        # Wellfound resume instructions
|-- config/
|   |-- config.yaml                 # General paths, database, and logging
|   |-- profile.yaml                # Candidate skills, education, and roles
|   `-- job_preferences.yaml        # Search, scoring, AI, and schedule options
|-- src/
|   |-- application/                 # Review queue, tracker, permissions
|   |-- config/                      # YAML configuration loading
|   |-- database/                    # Local database and job repository
|   |-- extraction/                  # Resume and job-description parsing
|   |-- ingestion/                   # Job-site browsers and job collection
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
- Python **3.10 or newer**. On Windows, Python 3.15 may require Microsoft
  C++ Build Tools to install PyYAML if pip cannot find a compatible wheel;
  Python 3.14 currently has a compatible wheel.
- A Naukri account for browsing and optional resume upload.
- An AI provider for resume tailoring (Groq, Gemini, Ollama, or Anthropic).

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

Install Python 3.14 if it is not already installed. With the Windows Python
install manager, run:

```powershell
py install 3.14
```

Then create the environment and install the dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

If the Python launcher is unavailable, install Python 3.14 and use
`python -m venv .venv` in the first command. Python 3.10+ is supported, but
Python 3.14 is recommended on Windows to avoid building PyYAML from source.

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

The default configuration uses Groq with Ollama as a local fallback. Put your
key in the project root `.env` file:

```text
GROQ_API_KEY=your_key_here
```

The configured Groq model is `openai/gpt-oss-120b`; override it with
`GROQ_MODEL` if needed. Keep API keys out of source files, command history,
and chat messages.

**Groq with local Ollama fallback**

1. Create an API key using [GroqCloud](https://console.groq.com/keys).
2. Create a `.env` file in the project root containing:

   ```text
   GROQ_API_KEY=your_key_here
   ```

3. Install [Ollama](https://ollama.com/download), then download the configured
   fallback model:

   ```powershell
   ollama pull qwen3:1.7b
   ```

   Keep Ollama running when you use it as a fallback. This smaller model is
   configured to reduce memory use on machines that cannot load qwen3:8b.
   Set `OLLAMA_FALLBACK_MODEL` in `.env` to override the fallback model.

Resume text and job descriptions are sent to the selected cloud AI when using
Groq, Gemini, or Anthropic. Review the provider's current privacy, data-use,
pricing, and model-availability terms before sending personal information.
Ollama processes requests locally on your computer.

**Ollama only**

Set `provider: ollama` and `model: qwen3:8b` under `resume_tailoring` in
`config\job_preferences.yaml`. Remove or comment out the
`fallback_provider` setting if you do not want a second provider.

To switch to Gemini or Anthropic, set `provider` and `model` in
`config\job_preferences.yaml`, then set `GEMINI_API_KEY` or
`ANTHROPIC_API_KEY` in `.env`.

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
.\.venv\Scripts\python.exe main.py --setup-shine-session
.\.venv\Scripts\python.exe main.py --setup-hirist-session
.\.venv\Scripts\python.exe main.py --setup-wellfound-session
```

Each platform has its own saved browser-profile directory under `data\`.
These directories are sensitive. Complete sign-in, OTP, CAPTCHA, and
verification yourself in the visible browser.

## Run the pipeline

### Run once now

```powershell
.\.venv\Scripts\python.exe main.py
```

The app searches jobs and may prompt you to review matching listings in the
terminal. Keep the terminal open and available for input during an interactive
run.

Run Naukri explicitly without changing the existing behavior:

```powershell
.\.venv\Scripts\python.exe main.py --search-naukri
```

To search Instahyre separately and add its visible listings to the same local
review queue without submitting applications:

```powershell
.\.venv\Scripts\python.exe main.py --search-instahyre
```

See [HOW_TO_RUN_INSTAHYRE.txt](./HOW_TO_RUN_INSTAHYRE.txt) for details.

To search Shine separately, score fresh listings, and create eligible
job-specific resume drafts without submitting applications:

```powershell
.\.venv\Scripts\python.exe main.py --search-shine
```

See [HOW_TO_RUN_SHINE.txt](./HOW_TO_RUN_SHINE.txt) for details.

Job-search adapters currently exist for Naukri, Instahyre, and Shine. The
Shine adapter skips listings without a verifiable posting age inside the
configured freshness window or without a full job description. Foundit,
Indeed, Hirist, and Wellfound do not yet have verified job-listing search
adapters; their commands cover resume uploads and supported profile actions.

The configured minimum score (75 by default) is this project's 0-100
job-to-resume relevance score, not a platform-provided ATS score. Tailored
resume drafts are created only at or above the threshold and only when a full
job description is available. The score is a prioritization aid; review each
listing and draft yourself.

To update Foundit only, without running a Naukri search:

```powershell
.\.venv\Scripts\python.exe main.py --update-foundit-profile
```

To update Naukri only, without running the job search:

```powershell
.\.venv\Scripts\python.exe main.py --update-naukri-profile
```

The command displays the proposed field values and changes them only after
you type `APPLY`. A normal scheduled run does not apply headline, skills,
employment, or project changes without that confirmation.

For individual resume updates, use the matching command:

```powershell
.\.venv\Scripts\python.exe main.py --update-foundit-profile
.\.venv\Scripts\python.exe main.py --update-indeed-profile
.\.venv\Scripts\python.exe main.py --update-shine-profile
.\.venv\Scripts\python.exe main.py --update-hirist-profile
.\.venv\Scripts\python.exe main.py --update-wellfound-profile
```

To update all enabled platforms once without starting the Naukri job search:

```powershell
.\.venv\Scripts\python.exe main.py --update-all-profiles
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

### Generate daily headline and About proposals

Edit `profile_text_updates.platforms.<platform>.headline_prompt` and
`about_prompt` in `config\job_preferences.yaml` to customize each platform's
instructions. The feature uses the existing `resume_tailoring` provider and
API key from `.env`. The Naukri prompts incorporate the attached master
prompt's resume analysis, target roles, supported keyword research, ten
headline options, and recruiter-focused summary guidance. Each day's proposal
selects one unused headline and one About/summary; other master-prompt sections
are not generated by this headline/About feature. For example:

```powershell
.\.venv\Scripts\python.exe main.py --generate-profile-text naukri
.\.venv\Scripts\python.exe main.py --generate-profile-text foundit
.\.venv\Scripts\python.exe main.py --generate-profile-text indeed
.\.venv\Scripts\python.exe main.py --generate-profile-text instahyre
.\.venv\Scripts\python.exe main.py --generate-profile-text shine
.\.venv\Scripts\python.exe main.py --generate-profile-text hirist
.\.venv\Scripts\python.exe main.py --generate-profile-text wellfound
```

Use `--generate-profile-text all` to generate proposals for all enabled
platforms. The dated JSON files are saved in
`data\processed\profile_text`; used headlines are stored in
`data\profile_text_history.json`. The generator skips a proposal that already
exists for the current date and rejects a headline that repeats an earlier
one, retrying generation before reporting an error. Review the JSON and copy
approved text to your profile yourself. To apply only the reviewed Naukri
headline, run `main.py --apply-profile-text naukri` and type `APPLY` after
checking the displayed text. The command does not edit About/summary text or
publish generated fields on other platforms.
See [HOW_TO_RUN_PROFILE_TEXT.txt](./HOW_TO_RUN_PROFILE_TEXT.txt) for daily
Windows Task Scheduler setup, API-key configuration, and platform-specific
notes.

## What happens during a run

- If `naukri_profile.update_resume` is enabled, the app compares the source
  resume with the last confirmed upload. It attempts to upload only when the
  file has changed. Login expiry, verification, or upload-confirmation problems
  require manual attention.
- Foundit, Indeed, Shine, Hirist, and Wellfound can upload changed resumes.
  Each platform has a separate browser-profile directory and upload-state
  file. An upload is recorded only after the site displays a recognized
  success message; if a site changes or does not confirm the upload, check it
  manually and retry. The automation does not bypass login, CAPTCHA, or
  verification.
- Foundit can add missing resume-supported skills, employment entries, and
  projects. It preserves existing entries rather than replacing them. The
  configured AI provider extracts the proposed profile fields from the
  selected source resume. Indeed currently supports resume upload only.
- Naukri can update the resume headline and key skills and add missing
  resume-supported projects. Existing projects are preserved. Profile fields
  are processed from resume-supported information. Use
  `--update-naukri-profile` to run this without the job search.
- Indeed, Hirist, and Wellfound currently support resume upload only; they do
  not automatically edit profile fields or submit applications. Shine also
  updates its summary, skills, explicitly stated total experience, and current
  company/designation from resume-supported information. Shine does not expose
  supported project or education editors, and its certification form requires
  validity details not extracted from the resume, so those sections are left
  unchanged.
- Jobs scoring at or above `matching.minimum_score` (75 by default) receive
  separate job-specific DOCX and `.txt` drafts under
  `data\processed\resumes`. This is a job-relevance score, not an ATS score.
  When
  `resume_tailoring.upload_best_draft_to_profiles` is enabled, the highest
  scoring draft from the run is uploaded to each enabled resume platform.
  The source resume is not overwritten. Indeed and Hirist currently support
  resume upload only; profile-field editors are available only on Naukri,
  Foundit, and Shine for their supported fields.
- Use `--update-all-profiles` to force a fresh reconciliation of supported
  profile fields from the source resume, including Naukri, Foundit, and Shine.
- Each run searches up to `job_search.max_searches_per_run` role/location
  combinations, filters listings to `job_search.posted_within_hours`, and
  processes up to `job_search.max_jobs_per_run` listings (20 by default).
  Job discovery currently runs on Naukri and Instahyre only; other platform
  commands update resumes and, on supported sites, profile fields.
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
  universal ATS score. Tailoring does not guarantee or artificially raise a
  score to 90%; it only rephrases and prioritizes facts present in the source.
- Where a job description is available and the job meets the configured
  criteria, job-specific resume drafts are saved as DOCX and plain-text
  sidecar files under `data\processed\resumes`. Both drafts use only
  resume-supported facts and must be reviewed before use.
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
  browser sessions, or Shine session-state files. Shine's
  `data\shine_session_state.json` contains authentication cookies and
  session-storage values; treat it as a credential and keep it private.
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
