# Cloud Architecture Recommender

Build an inventory of AWS reference architectures by scraping and parsing the AWS
Architecture Center, then recommend the most relevant architectures for a set of
structured user requirements.

> **Status:** Under active development. See [`todo.md`](todo.md) for the current sprint
> and progress checklist.

---

## Overview

The system has four components:

1. **Scraper / Parser (Python)** — scrapes AWS architecture pages, extracts structured
   data (AWS services, use cases, characteristics), and stores it in MongoDB.
2. **Backend API (FastAPI)** — lists parsed architectures, exposes details, triggers
   scrape jobs, and serves recommendations.
3. **Recommendation Engine** — deterministic weighted scoring that ranks architectures
   against a 9-dimension requirements object and explains each match.
4. **Frontend (React + TypeScript)** — UI to trigger scraping, browse architectures, and
   get recommendations.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, Motor |
| Database | MongoDB 7.x |
| Frontend | React 18 + TypeScript (Vite, TanStack Query) |
| DevOps | Docker + Docker Compose |

## Repository Layout

```
.
├── backend/     # FastAPI app, scraper, recommendation engine
├── frontend/    # React + TypeScript web app
├── docker-compose.yml
├── CLAUDE.md    # Architecture rules & conventions (contributor reference)
└── todo.md      # Sprint breakdown & progress
```

## Getting Started

> Full Docker Compose setup instructions are added in Sprint 5 (S5.4). The steps below
> cover local development during the build-out.

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)

### Environment

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

### Run MongoDB

```bash
docker compose up -d mongo
```

### Backend (local)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`; check `http://localhost:8000/health`.

### Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

## Architecture & Design Decisions

_To be documented in Sprint 5 (S5.4): implemented approach, recommendation strategy,
and trade-offs._

## License

This project was created as a home assignment.
