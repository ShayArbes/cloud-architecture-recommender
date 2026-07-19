# Cloud Architecture Recommender

Build an inventory of AWS reference architectures by scraping and parsing the AWS
Architecture Center, then recommend the most relevant architectures for a set of
structured user requirements — with a transparent, deterministic score and a
human-readable explanation for every match.

---

## Overview

The system has four components:

1. **Scraper / Parser (Python)** — discovers and downloads AWS architecture pages
   (async, with retries, backoff, and robots.txt compliance), extracts structured data
   (AWS services, use cases, and the nine recommendation characteristics), and stores it
   in MongoDB. Parsing sits behind a `ArchitectureParser` interface with a deterministic
   rule-based parser and an optional Claude-API parser — **the app runs fully without an
   API key**.
2. **Backend API (FastAPI)** — lists parsed architectures, exposes details, triggers
   scrape jobs (as background tasks), and serves recommendations.
3. **Recommendation Engine** — deterministic weighted scoring that ranks architectures
   against a 9-dimension requirements object and explains each match. Same input always
   produces the same output.
4. **Frontend (React + TypeScript)** — UI to trigger scraping, browse/inspect
   architectures, submit requirements, and view ranked recommendations.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, Motor (async MongoDB) |
| Scraping | httpx (async) + BeautifulSoup4 |
| AI parsing (optional) | Claude API (`claude-sonnet-5`) behind an interface, with a deterministic fallback |
| Database | MongoDB 7.x |
| Frontend | React 18 + TypeScript (strict), Vite, TanStack Query |
| DevOps | Docker + Docker Compose (multi-stage builds, non-root images) |
| Quality | Ruff, mypy (strict), pytest / ESLint, Prettier, `tsc` |

---

## Quick Start (Docker Compose)

The fastest path — brings up MongoDB, the API, the built frontend, and seeds a demo
inventory automatically.

**Prerequisites:** Docker and Docker Compose.

```bash
# 1. (Optional) create a .env; sensible defaults apply if you skip this.
cp .env.example .env

# 2. Build and start the full stack.
docker compose up --build
```

Then open:

| Surface | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API (health) | http://localhost:8000/health |
| Interactive API docs (Swagger UI) | http://localhost:8000/docs |

On startup a one-shot `seed` service loads a curated catalogue of eight AWS reference
architectures (see [Seed data](#seed-data)), so the app is demonstrable immediately even
without live scraping. Seeding is idempotent — re-running `up` never creates duplicates.

To stop and remove the containers (keeping the MongoDB volume):

```bash
docker compose down
```

> **Ports already in use?** The host ports are configurable in `.env`
> (`FRONTEND_PORT`, `API_PORT`, `MONGO_HOST_PORT`).

---

## Local Development

Run MongoDB in Docker and the backend/frontend on the host for fast iteration.

### Environment

```bash
cp .env.example .env
```

Every variable is documented in [`.env.example`](.env.example). For host-based
development set `MONGO_URI=mongodb://localhost:27017` (inside Compose it is `mongo`).

### MongoDB

```bash
docker compose up -d mongo
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000` (docs at `/docs`). Seed the inventory:

```bash
python -m app.db.seed
```

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

### Quality gates

```bash
# Backend
cd backend && ruff check . && ruff format --check . && mypy app && pytest

# Frontend
cd frontend && npm run lint && npm run build
```

---

## API

Base path `/api/v1`; interactive docs at `/docs`, OpenAPI schema at
`/openapi.json`. Errors use a consistent envelope:
`{ "error": { "code": ..., "message": ..., "details": {} } }`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/architectures` | Paginated list (`limit`, `offset`, optional `use_case`, `tag`) |
| `GET` | `/architectures/{slug}` | Full architecture detail |
| `POST` | `/scrape` | Trigger a scrape job (background); returns `202` with `job_id` |
| `GET` | `/scrape/jobs/{job_id}` | Job status + stats (polled by the frontend) |
| `GET` | `/scrape/jobs` | Recent job history |
| `POST` | `/recommendations` | 9-field requirements → ranked recommendations |
| `POST` | `/recommendations/flexible` | Same 9 fields as **free text**, normalized to the enums (bonus) |
| `GET` | `/health` | Liveness + MongoDB ping (Docker healthcheck) |

### Recommendation request

All nine fields are required enums (see `/docs` for the exact value sets):

```json
{
  "use_case": "ecommerce",
  "scale": "medium",
  "traffic_pattern": "bursty",
  "latency_sensitivity": "medium",
  "processing_style": "event_driven",
  "data_intensity": "medium",
  "availability_requirement": "high",
  "ops_preference": "managed_services",
  "budget_sensitivity": "medium"
}
```

The response returns the top matches, each with a `score` in `[0, 1]`, a per-dimension
`match_breakdown`, and a template `explanation` generated from that breakdown.

#### Free-text requirements (bonus)

`POST /recommendations/flexible` accepts the same nine fields as **free strings**
(e.g. `"use_case": "online store"`, `"ops_preference": "serverless"`, `"scale": "big"`).
A deterministic normalization step maps each value to the nearest enum — case- and
separator-insensitive, with a curated synonym table — and then hands a strict request
to the **same** scoring engine. An unmappable value returns `422` with a
`UNRECOGNIZED_REQUIREMENT` code naming the field, the received value, and the allowed
options. The engine itself is never changed or bypassed (see
`services/recommendation/normalization.py`).

---

## Architecture & Design Decisions

### Backend — layered, one-directional dependencies

```
routers  →  services  →  repositories  →  db (Motor client)
```

- **Routers** handle HTTP only; **services** hold all business logic and are pure enough
  to unit-test without HTTP or a database; **repositories** are the only place MongoDB
  queries live and return Pydantic domain models, never raw dicts.
- Services depend on repository **protocols** (`typing.Protocol`), not on Motor, so they
  can be tested with in-memory fakes (dependency inversion).
- The Motor client is created in the FastAPI **lifespan** and injected via `Depends` — no
  module-level singletons. The API starts and reports health even while MongoDB is
  briefly unreachable.

### Scraper — strategy pattern, resilient by design

Parsing is an `ArchitectureParser` interface; adding an LLM parser or a new source parser
means adding a class, not editing existing ones (open/closed). Network calls use timeouts
and retry-with-backoff; a single failed page is recorded on the job document and the run
continues — one bad page never aborts a scrape, and a failed scrape never crashes the API.

### Recommendation engine — deterministic and explainable

- **Nine dimensions**, compared field-for-field against each architecture's stored
  `characteristics`. Scoring is a single O(n·f) pass over `n` candidates × `f = 9` fields;
  the candidate set is fetched **once** (no N+1).
- Per-dimension compatibility uses explicit O(1) lookup matrices: exact match scores 1.0,
  "adjacent" values earn partial credit (e.g. requested `scale=medium` vs a design that
  supports `["large"]`). Dimension **weights** (use case weighted highest) are named
  constants in one place.
- The final score is a weighted sum normalized to `[0, 1]`; ties break by most recent
  `parsed_at`. The **explanation is generated from the breakdown**, so it can never
  contradict the score. The LLM is allowed in parsing/enrichment only — **never** in
  scoring.

### Frontend — hooks for logic, components for rendering

Data fetching and mutations live in TanStack Query hooks; components stay presentational.
Every server interaction renders all four states — loading, error (with retry), empty, and
success. Types mirror the backend schemas exactly (`strict` TypeScript, no `any`).

### Key trade-offs

- **No ODM (repository pattern over Motor).** More boilerplate than an ODM, but keeps
  MongoDB access in one layer and business logic trivially unit-testable.
- **Deterministic scoring over an LLM ranker.** Reproducible, explainable, and free to
  run; the cost is hand-authored compatibility matrices instead of learned relevance.
- **Characteristics mirror the request shape.** Denormalizing the nine dimensions onto each
  architecture makes matching a direct comparison and keeps the hot path index-friendly,
  at the cost of re-parsing if the dimensions change (hence `parser_version`).
- **Build-time frontend config.** `VITE_API_BASE_URL` is baked into the bundle at build
  time (a Docker build arg), trading runtime flexibility for a simpler static deployment.

---

## Seed data

The curated catalogue lives in `backend/app/db/seed_data.py` — eight AWS reference
architectures spanning all nine dimensions and every use case, so recommendations return
varied results out of the box. It is upserted by `source_url` exactly like a real scrape,
so seeding is idempotent.

- **Compose:** the `seed` service runs automatically on `docker compose up`.
- **Manually:** `docker compose run --rm seed`, or locally `python -m app.db.seed`.

To gather live data instead, trigger a scrape from the UI or `POST /api/v1/scrape`.

---

## Repository Layout

```
.
├── backend/            # FastAPI app, scraper, recommendation engine
│   ├── app/
│   │   ├── core/         # config, logging, constants, errors
│   │   ├── models/       # Pydantic domain models & enums
│   │   ├── schemas/      # API request/response DTOs
│   │   ├── routers/      # HTTP layer (no business logic)
│   │   ├── services/     # business logic (scrape, recommendation)
│   │   ├── repositories/ # MongoDB access only
│   │   ├── scraper/      # fetchers + parsers (strategy pattern)
│   │   └── db/           # client, indexes, seed
│   └── tests/            # mirrors app/
├── frontend/           # React + TypeScript web app
│   └── src/
│       ├── api/          # typed API client
│       ├── features/     # architectures, recommendations, scraping
│       ├── components/   # shared presentational components
│       └── hooks/        # shared hooks
├── docker-compose.yml  # mongo + backend + seed + frontend
├── .env.example        # documented environment variables
├── CLAUDE.md           # architecture rules & conventions (contributor reference)
└── todo.md             # sprint breakdown & progress
```

## License

Created as a home assignment.
