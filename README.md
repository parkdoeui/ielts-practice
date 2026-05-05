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

### 2. Backend (progress tracking) — optional

Requires Docker for PostgreSQL:

```bash
docker-compose up -d          # start Postgres
cd backend
pip install -r requirements.txt
uvicorn main:app --reload     # http://localhost:8000
```

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env`.

The frontend works **without** the backend — sessions are still saved to localStorage. When the backend is unavailable, the results page shows that the attempt was stored locally only.

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

Generate a range of tests:

```bash
python3 crawl_range.py 3 10 --output ../frontend/src/data/tests
```

Use AI-assisted validation/repair during crawl:

```bash
python3 main.py crawl "<test-url>" --output ../frontend/src/data/tests --ai-auto --project <your-gcp-project>
python3 crawl_range.py 11 20 --output ../frontend/src/data/tests --ai-auto --project <your-gcp-project> --workers 4
```

AI mode notes:

- `--ai-validate` runs AI validation only and fails the crawl if Gemini finds structural issues.
- `--ai-repair` always runs AI repair before saving.
- `--ai-auto` validates first and only repairs if needed. This is the recommended mode.
- AI modes require a Vertex AI GCP project via `--project`.

Output:

- Test JSON files are written to `frontend/src/data/tests/test-<n>.json`.
- AI repairs also write `frontend/src/data/tests/test-<n>.repair-report.json`.

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

## Environment Config

Frontend `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
VITE_VALID_PASSCODE=your-passcode-here
```

Backend `backend/.env`:

```bash
DATABASE_URL=postgresql://ielts:ielts@localhost:5432/ielts
VALID_PASSCODE=your-passcode-here
```

Architecture:

- The browser uses `VITE_VALID_PASSCODE` to unlock the app and stores the successful passcode in localStorage.
- On submit, the frontend saves the result to localStorage immediately, then awaits `POST /api/sessions`.
- The backend validates the submitted passcode against `VALID_PASSCODE` before saving or returning session data.
- `GET /api/sessions` and `GET /api/progress` are passcode-scoped and backed by PostgreSQL when the API is available.
- localStorage remains the fallback cache if the backend is down or misconfigured.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Tailwind CSS 4, React Router 7 |
| Backend | FastAPI, SQLAlchemy 2, PostgreSQL |
| Crawler | Python, Playwright, BeautifulSoup4, Pydantic |
| Local DB | Docker Compose (Postgres 17) |
