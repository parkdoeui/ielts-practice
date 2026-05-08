# IELTS Practice Platform

A self-hosted IELTS Academic Reading practice tool for friends. Take timed reading tests, review answers, and track progress over time.

## Structure

```
ielts-practice/
├── frontend/    # React 19 + Vite + Tailwind 4 SPA
├── backend/     # FastAPI + PostgreSQL API
└── crawler/     # Python + Playwright web crawler
```

## Quick Start

### 1. Frontend (test-taking UI)

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env` from `frontend/.env.example` before starting. Open http://localhost:5173.

### 2. Backend (auth + progress tracking)

Requires Docker for PostgreSQL:

```bash
docker-compose up -d          # start Postgres
cd backend
pip install -r requirements.txt
uvicorn main:app --reload     # http://localhost:8000
```

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`.

The backend provides the passcode gate (server-side) and progress tracking. Sessions are still saved to localStorage immediately, but syncing/progress requires the API.

### 3. Crawler — add new tests

```bash
cd crawler
python3 -m pip install -r requirements.txt
playwright install chromium
```

Generate one test JSON file:

```bash
python3 main.py crawl "<test-url>" --output ../frontend/src/data/tests
```

Example:

```bash
python3 main.py crawl "https://practicepteonline.com/ielts-reading-test-21/" --output ../frontend/src/data/tests
```

Generate one writing test JSON file:

```bash
python3 main.py crawl-writing "https://practicepteonline.com/ielts-writing-test-1/" --output ../frontend/src/data/writing-tests
```

Generate a range of tests:

```bash
python3 crawl_range.py 3 10 --output ../frontend/src/data/tests
```

Use AI-assisted validation/repair during crawl:

```bash
python3 main.py crawl "<test-url>" --output ../frontend/src/data/tests --ai-auto --project <your-gcp-project>
python3 crawl_range.py 11 20 --output ../frontend/src/data/tests --ai-auto --project <your-gcp-project> --workers 4
```

Use AI-assisted validation for writing crawl:

```bash
python3 main.py crawl-writing "https://practicepteonline.com/ielts-writing-test-1/" --output ../frontend/src/data/writing-tests --ai-validate --project <your-gcp-project>
```

AI mode notes:

- `--ai-validate` runs AI validation only and fails the crawl if Gemini finds structural issues.
- `--ai-repair` always runs AI repair before saving.
- `--ai-auto` validates first and only repairs if needed. This is the recommended mode.
- AI modes require a Vertex AI GCP project via `--project`.

Output:

- Test JSON files are written to `frontend/src/data/tests/test-<n>.json`.
- AI repairs also write `frontend/src/data/tests/test-<n>.repair-report.json`.
- Writing test JSON files are written to `frontend/src/data/writing-tests/writing-test-<n>.json`.

After generating new test files, rebuild the frontend:

```bash
cd ../frontend
npm run build
```

## Features

- **9 IELTS question types** — True/False/NG, Multiple Choice (single & multi-answer), Matching Headings, Matching Information, Sentence/Summary/Note Completion, Diagram Labeling
- **60-minute countdown timer** — auto-submits at 0:00, flashes red at 5 min
- **Split-pane layout** — passage left, questions right (mobile: toggle tabs)
- **Instant grading** — score, band estimate (4.0–9.0), per-question review
- **Progress dashboard** — score history, band trend chart, per-question-type accuracy
- **Passcode gate** — simple access control for friends-only use
- **Writing mode** — Task 1 + Task 2 timed writing flow with backend AI grading feedback

## Environment Config

Frontend `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
```

Backend `backend/.env`:

```bash
DATABASE_URL=postgresql://ielts:ielts@localhost:5432/ielts
VALID_PASSCODE=your-passcode-here
FRONTEND_ORIGIN=http://localhost:5173
COOKIE_SECURE=false
VERTEX_PROJECT=your-gcp-project
VERTEX_CREDENTIALS_JSON={"type":"service_account",...}
VERTEX_LOCATION=us-central1
WRITING_GRADER_MODEL=gemini-2.5-pro
```

For hosted backend deployments, `VERTEX_PROJECT` should be paired with either platform-provided Google Application Default Credentials or `VERTEX_CREDENTIALS_JSON` containing a service account JSON. This matches the crawler's Vertex AI path. `GEMINI_API_KEY`/`VERTEX_API_KEY` are fallback API-key modes and use Gemini Developer API quota instead of Vertex AI quota.

Architecture:

- The browser prompts for a passcode and sends it to `POST /api/auth/login`.
- The backend validates against `VALID_PASSCODE` and sets an `HttpOnly` cookie for subsequent requests.
- On submit, the frontend saves the result to localStorage immediately, then attempts to sync via `POST /api/sessions` (cookie-auth).
- `GET /api/sessions` and `GET /api/progress` are backed by PostgreSQL and require the auth cookie.
- Writing submissions are sent to `POST /api/writing-sessions`; backend calls Vertex AI and stores criterion-level feedback + sample answers + action points.
- localStorage remains the local cache for results even if syncing fails.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Tailwind CSS 4, React Router 7 |
| Backend | FastAPI, SQLAlchemy 2, PostgreSQL |
| Crawler | Python, Playwright, BeautifulSoup4, Pydantic |
| Local DB | Docker Compose (Postgres 17) |
