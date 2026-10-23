# Naukri job matching and resume drafts

This project searches configured Naukri job listings, scores them against
`config/profile.yaml` and `config/job_preferences.yaml`, and stores matching
jobs for review. The scheduled workflow can also create a separate AI-assisted
resume draft for each sufficiently matched job.

## Setup

1. Use Python 3.9 or newer and install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   playwright install chromium
   ```

2. Put a text-based PDF resume at `data\resume.pdf`. PDF, DOCX, TXT, and
   Markdown source files are supported; change `resume_path` in
   `config\job_preferences.yaml` if you use another location. Scanned/image
   PDFs without extractable text are not supported. Replace this source file
   with your latest version when you update your resume in the evening.

   Candidate skills and role preferences belong in
   `config\profile.yaml` and `config\job_preferences.yaml`; do not put profile
   information or Naukri passwords in `.env`. The profile YAML guides job
   matching. The automated profile step uploads the source resume only; it
   does not edit Naukri's headline or skills fields.

3. Gemini is the primary provider. Create an API key in
   [Google AI Studio](https://aistudio.google.com/apikey), then add it to the
   root `.env` file as a single line:

   ```text
   GEMINI_API_KEY=your_key_here
   ```

   The app loads this local file automatically. `.env` is excluded from Git;
   do not commit the key or paste it into chat. Google offers a free tier for selected models, subject to current
   model availability and quotas; check the current
   [Gemini API pricing and data-use terms](https://ai.google.dev/gemini-api/docs/pricing)
   before sending your resume. Resume and job-description text is sent to
   Google's API; free-tier data-use terms may allow content to be used to
   improve Google products.

   The primary model is `gemini-3.8-flash`. If that model is unavailable to
   your API key or free tier, choose a currently available model in
   `config\job_preferences.yaml`.

   Ollama is configured as the local fallback. Install
   [Ollama](https://ollama.com/download), then in PowerShell run:

   ```powershell
   ollama pull qwen3:8b
   ```

   Keep Ollama running. If Gemini times out or returns a temporary service
   error, the app tries the local Qwen model. A successful Gemini request sends
   your resume text and the job description to Google's API; the local fallback
   runs on your computer.

   To use Ollama only, set `provider: ollama` and `model: qwen3:8b` in
   `config\job_preferences.yaml`, and remove or comment out `fallback_provider`.

   Anthropic remains available if you select `provider: anthropic` in that
   config and set `ANTHROPIC_API_KEY` in your Windows user environment. Never
   put passwords or API keys in source files or send them in chat.

4. Adjust target roles, locations, experience, matching threshold, daily
   search limit, and schedule in `config\job_preferences.yaml`.

## Run

Run a scan immediately and review its queue interactively:

```powershell
python main.py
```

Before the first automatic profile resume update, create a local signed-in
browser session:

```powershell
python main.py --setup-naukri-session
```

Sign in yourself in the opened browser, complete any verification manually,
then return to the terminal and press Enter. The session is stored locally in
`data\naukri_browser_profile`; your Naukri password is never saved by this app.

Run the daily scheduler in the current terminal:

```powershell
python main.py --schedule
```

The default run time is 09:30 Asia/Kolkata. The process must remain running;
it waits until the next scheduled time before its first run. On Windows, use
Task Scheduler to start `python main.py --schedule` when you sign in if you
want the process to start automatically after login.

At each run, the app uploads `data\resume.pdf` to your Naukri profile only if
its contents changed since the last confirmed upload. Replace that file each
evening; do not replace the generated job-specific drafts. If the upload
cannot be confirmed or the saved login expires, the app reports it and
continues with the job search. Finish sign-in or verification manually and run
the app again.

Each run rotates through up to eight configured role/location searches,
requests Naukri's one-day posting filter, and locally skips listings shown as
older than 24 hours or without a recognized posting age. It then processes up
to 20 unique recent listings. Search combinations rotate by day so the full
configured set is covered over time. Naukri's displayed age can be rounded;
the site-side filter is used together with the local age check. CAPTCHA and
verification pages stop the run and require manual action.

## Review and privacy

AI-generated DOCX drafts are saved in `data\processed\resumes`. They are
separate from the source resume and must be checked for accuracy before use.
The tailoring prompt explicitly prohibits inventing candidate facts, but
AI-generated content still needs human review. Local model speed and quality
depend on your computer and the selected model.

Jobs that meet the match threshold remain in the review queue. The project
does not bypass account verification or submit job applications. Review each
job and AI-generated draft yourself, then apply on Naukri manually.

The local resume, generated drafts, browser login session, and upload state are
excluded from Git by `.gitignore`.
