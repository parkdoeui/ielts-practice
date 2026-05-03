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

Open http://localhost:5173. Default passcode: `ielts2024`

### 2. Backend (progress tracking) — optional

Requires Docker for PostgreSQL:

```bash
docker-compose up -d          # start Postgres
cd backend
pip install -r requirements.txt
uvicorn main:app --reload     # http://localhost:8000
```

Copy `.env.example` to `.env` and set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local`.

The frontend works **without** the backend — sessions are saved to localStorage. The progress dashboard shows local data as a fallback.

### 3. Crawler — add new tests

```bash
cd crawler
pip install -r requirements.txt
playwright install chromium
python main.py crawl <url> --output ../frontend/src/data/tests/
```

Then rebuild the frontend (`npm run build`) to include the new test JSON.

## Features

- **9 IELTS question types** — True/False/NG, Multiple Choice (single & multi-answer), Matching Headings, Matching Information, Sentence/Summary/Note Completion, Diagram Labeling
- **60-minute countdown timer** — auto-submits at 0:00, flashes red at 5 min
- **Split-pane layout** — passage left, questions right (mobile: toggle tabs)
- **Instant grading** — score, band estimate (4.0–9.0), per-question review
- **Progress dashboard** — score history, band trend chart, per-question-type accuracy
- **Passcode gate** — simple access control for friends-only use

## Changing the Passcode

Edit `frontend/src/components/AccessGate.tsx`:

```ts
const VALID_PASSCODE = "your-passcode-here";
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Tailwind CSS 4, React Router 7 |
| Backend | FastAPI, SQLAlchemy 2, PostgreSQL |
| Crawler | Python, Playwright, BeautifulSoup4, Pydantic |
| Local DB | Docker Compose (Postgres 17) |
