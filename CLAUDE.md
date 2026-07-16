# CLAUDE.md — Cloud Architecture Recommender

> **This file is the single source of truth for architecture rules and conventions on
> this project.** Read it in full before writing any code. All architectural decisions,
> conventions, and workflows defined here are **mandatory** unless the project owner
> explicitly overrides them. Project state (user stories, sprints, progress) lives
> exclusively in [`todo.md`](todo.md) — see §7.

---

## 1. Project Overview

**Goal:** Build a cloud-architecture scraping, parsing, and recommendation application
(the "InfrOS" home assignment). The system builds an inventory of AWS reference
architectures and recommends the most relevant ones based on structured user requirements.

**The system has four components:**

1. **Scraper/Parser (Python)** — scrapes AWS cloud architecture pages (AWS Architecture
   Center / reference architectures / solution library), extracts structured data
   (services used, use cases, characteristics), and persists it to MongoDB.
2. **Backend API (FastAPI)** — exposes endpoints to list parsed architectures, view
   details, trigger new scrape jobs, and get recommendations.
3. **Recommendation Engine** — deterministic weighted-scoring engine that matches user
   requirements (9 structured fields) against the architecture inventory and returns
   ranked results with human-readable explanations.
4. **Frontend (React + TypeScript)** — UI to trigger scraping, browse/inspect
   architectures, submit requirements, and view recommendations.

**Evaluation context:** This is a graded home assignment submitted as a GitHub repository.
**Code quality, architecture, Git history, and the README are all evaluated.** Every
commit and every file is part of the deliverable. Sloppy commits, dead code, or missing
error handling directly hurt the submission.

**Repository layout (monorepo):**

```
cloud-architecture-recommender/
├── CLAUDE.md                  # This file — architecture rules & conventions, read first
├── todo.md                    # User stories + progress checklist (all task tracking)
├── MEMORY.md                  # Long-term agent memory: decisions, resolved bugs, lessons
├── .agents/                   # Per-role agent context files (personas & boundaries)
├── README.md                  # Setup, run, architecture explanation, trade-offs
├── docker-compose.yml         # Orchestrates mongo + backend + frontend
├── .env.example               # All required env vars, documented, no secrets
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml         # Deps + ruff + mypy + pytest config
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, lifespan, exception handlers
│   │   ├── core/              # config (pydantic-settings), logging, constants, errors
│   │   ├── models/            # Pydantic domain models & enums
│   │   ├── schemas/           # API request/response schemas (DTOs)
│   │   ├── routers/           # HTTP layer only — no business logic
│   │   ├── services/          # Business logic (scrape orchestration, recommendation)
│   │   ├── repositories/      # MongoDB access only — no business logic
│   │   ├── scraper/           # Fetchers + parsers (strategy pattern)
│   │   └── db/                # Client setup, index creation
│   └── tests/                 # Mirrors app/ structure
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json          # strict: true
    └── src/
        ├── api/               # Typed API client + generated/handwritten types
        ├── features/          # Feature folders (architectures, recommendations, scraping)
        ├── components/        # Shared presentational components
        ├── hooks/             # Shared hooks
        └── App.tsx
```

---

## 2. Tech Stack (Exact — Do Not Substitute)

| Layer | Technology | Notes |
|---|---|---|
| Language (backend) | **Python 3.11+** | Use modern syntax: `X | None`, `match`, `Self`, dataclasses/Pydantic |
| API framework | **FastAPI** (latest stable) | Fully async; app-factory pattern; lifespan for startup/shutdown |
| Validation | **Pydantic v2** | All boundaries validated; `pydantic-settings` for config |
| Database | **MongoDB 7.x** | Via **Motor** (async driver). No ODM — repository pattern instead |
| Scraping | **httpx** (async) + **BeautifulSoup4** | Respect robots.txt, rate-limit, retry with backoff |
| AI parsing (optional) | **Claude API** (`claude-sonnet-5`) | Behind a `Parser` interface; deterministic fallback parser **must** exist so the app runs without an API key |
| Backend tooling | **Ruff** (lint + format), **mypy** (strict), **pytest** + **pytest-asyncio** | All must pass before every commit |
| Language (frontend) | **TypeScript** (strict mode, no `any`) | `tsconfig`: `strict`, `noUncheckedIndexedAccess` |
| UI framework | **React 18+** | Functional components + hooks only |
| Build tool | **Vite** | |
| Server state | **TanStack Query (React Query)** | All API calls go through it — no ad-hoc `useEffect` fetching |
| Frontend tooling | **ESLint** + **Prettier** | Must pass before every commit |
| Containerization | **Docker** + **Docker Compose** | One Dockerfile per component; multi-stage builds |

**Dependency policy:** Keep dependencies minimal. Do not add a library without a clear
justification recorded in the commit message. No heavyweight state managers (Redux etc.)
— React Query + local state is sufficient at this scale.

---

## 3. Architectural Guidelines (Mandatory)

### 3.1 Backend — Layered Architecture

Strict one-directional dependency flow:

```
routers  →  services  →  repositories  →  db (Motor client)
   ↓            ↓              ↓
schemas      models         models
```

- **Routers** (`app/routers/`): HTTP concerns only — parse request, call one service
  method, shape the response. **Zero business logic.** No direct DB access, ever.
- **Services** (`app/services/`): All business logic. Pure Python where possible so it is
  unit-testable without HTTP or DB. Receive repositories via constructor injection.
- **Repositories** (`app/repositories/`): The **only** place MongoDB queries live. Return
  domain models (Pydantic), never raw dicts, never Motor cursors, to callers.
- **Schemas vs Models:** `schemas/` are API DTOs (request/response shapes); `models/` are
  internal domain models. Never expose a domain model directly if it leaks internal fields
  — map explicitly.
- **Dependency injection:** Use FastAPI `Depends` to wire repositories → services →
  routers. No module-level singletons of DB clients; the Motor client is created in the
  app lifespan and injected.

### 3.2 SOLID — Concrete Rules for This Project

- **S — Single Responsibility:** One service = one domain concern (`ScrapeService`,
  `RecommendationService`, `ArchitectureService`). A function does one thing; if you need
  the word "and" to describe it, split it. Max ~40 lines per function as a guideline.
- **O — Open/Closed:** Parsers implement an abstract `ArchitectureParser` interface
  (`parse(raw_html) -> ParsedArchitecture`). Adding an LLM parser or a new source parser
  means adding a class, not modifying existing ones.
- **L — Liskov:** Any `ArchitectureParser` implementation must be swappable without the
  caller knowing. Same for repositories (define abstract repository protocols with
  `typing.Protocol`).
- **I — Interface Segregation:** Keep protocols small and role-specific
  (`ArchitectureReader`, `ArchitectureWriter`) rather than one giant repository interface.
- **D — Dependency Inversion:** Services depend on repository **protocols**, not on Motor
  or concrete Mongo classes. This is what makes services unit-testable with in-memory fakes.

### 3.3 Clean Code Rules (Both Stacks)

- **Naming:** Intention-revealing, no abbreviations (`architecture_repository`, not
  `arch_repo`). Booleans read as predicates (`is_stale`, `has_diagram`).
- **No magic values:** Every enum/constant lives in `core/constants.py` (backend) or a
  `constants.ts` (frontend). The 9 recommendation enums are defined **once** and imported
  everywhere.
- **Type hints everywhere:** Backend must be `mypy --strict` clean. Frontend must compile
  with `strict: true` and zero `any`/`@ts-ignore` (use `unknown` + narrowing when needed).
- **Docstrings/comments:** Public functions get a one-line docstring stating *what/why*.
  Do not comment *what the next line does*; comment only non-obvious constraints.
- **No dead code:** Never commit commented-out code, unused imports, or `console.log`/
  `print` debugging. Use structured logging (`logging` w/ config in `core/logging.py`).
- **Small modules:** If a file exceeds ~300 lines, it almost certainly has more than one
  responsibility — split it.

### 3.4 React / TypeScript Conventions

- **Feature folders:** `src/features/<feature>/` contains that feature's components,
  hooks, and types. Shared pieces graduate to `src/components/` / `src/hooks/` only when
  used by 2+ features.
- **Logic in hooks, rendering in components:** Data fetching and mutations live in custom
  hooks wrapping React Query (`useArchitectures()`, `useTriggerScrape()`,
  `useRecommendations()`). Components stay presentational.
- **Typed API layer:** `src/api/` contains one client module per resource with explicit
  request/response TypeScript types that mirror the backend schemas **exactly**. No
  untyped `fetch` calls scattered in components.
- **Every server interaction renders all four states:** loading, error (with a retry
  affordance), empty, and success. This is checked in review — no exceptions.
- **Error boundary** at the app root; user-facing errors are friendly messages, never raw
  stack traces or Axios error dumps.
- **Forms:** The recommendation form is fully typed; enum options are derived from the
  shared constants, never hardcoded string literals in JSX.

### 3.5 Error Handling (Backend)

- Custom exception hierarchy in `core/errors.py`:
  `AppError` → `NotFoundError`, `ValidationError`, `ScrapeError`, `ExternalServiceError`.
- FastAPI **exception handlers** map these to a single consistent JSON error envelope:

  ```json
  { "error": { "code": "ARCHITECTURE_NOT_FOUND", "message": "...", "details": {} } }
  ```

- **Never** let a raw exception reach the client; the generic handler returns 500 with a
  safe message and logs the full traceback.
- **Scraper resilience:** network calls use timeouts + retry with exponential backoff
  (max 3 attempts); one failed page must not abort the whole scrape job — record the
  failure in the job document and continue. The API process must never crash because a
  scrape failed.
- Validation errors (Pydantic) return 422 with field-level details.

### 3.6 Performance & Complexity Requirements

- **Recommendation scoring is O(n·f)** — a single pass over n candidate architectures
  scoring f (=9) fields each. No nested candidate-vs-candidate comparisons, no repeated
  DB round-trips inside the scoring loop (fetch candidates once).
- **Compatibility lookups are O(1)** — dict-based matrices, never list scans.
- **List endpoints are paginated** (`limit`/`offset` or cursor, default limit 20, max 100)
  and backed by an index; never return unbounded collections.
- **No N+1 queries:** batch reads; the recommendation endpoint makes exactly one query to
  fetch candidates.
- **Async I/O throughout** the backend — no blocking calls (`requests`, `time.sleep`) in
  the event loop. CPU-light scoring may run inline; scraping runs as a background task.
- **Indexes are declared in code** (`db/indexes.py`, ensured at startup) — see §5.

---

## 4. Git & Version Control Workflow (Strict)

### 4.1 Conventional Commits — Required Format

```
<type>(<scope>): <subject>

[optional body — the WHY, wrapped at 72 chars]
```

- **Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `style`.
- **Scopes for this repo:** `scraper`, `api`, `reco`, `frontend`, `db`, `docker`, `repo`.
- **Subject:** imperative mood ("add", not "added"/"adds"), lowercase, no trailing
  period, ≤ 72 characters.
- Examples:
  - `feat(scraper): parse AWS service list from architecture pages`
  - `feat(reco): add weighted scoring across the 9 requirement dimensions`
  - `fix(api): return 404 instead of 500 for unknown architecture id`
  - `docs(repo): add docker-compose setup instructions to README`
  - `test(reco): cover partial-match scoring for adjacent scale values`

### 4.2 Atomic Commits

- **One logical change per commit.** A commit must not mix a feature with an unrelated
  refactor, or backend with frontend changes, unless they are inseparable.
- Every commit must leave the repo in a **working state**: code compiles, linters pass,
  tests pass. Never commit broken intermediate states.
- Commit at each completed increment of a user story — small, frequent, reviewable.
- **Never** use `git add .` blindly; stage intentionally and review the diff before
  committing. Never commit `.env`, credentials, `node_modules`, `__pycache__`, or build
  artifacts (maintain `.gitignore` from Sprint 0).

### 4.3 Branches

- Branch names: `feat/<short-slug>`, `fix/<short-slug>`, `docs/<short-slug>`
  (e.g., `feat/recommendation-engine`).
- `main` is always green (builds + tests pass). Work on story branches and merge when
  the story's Definition of Done is met.
- No force-pushes to `main`. Prefer new commits over amending already-pushed history.

---

## 5. Database Schema (MongoDB)

Database name: `cloud_arch_db`. Two collections.

### 5.1 `architectures`

One document per scraped-and-parsed AWS reference architecture.

```jsonc
{
  "_id": ObjectId,
  "slug": "serverless-ecommerce-platform",     // unique, derived from title/url
  "title": "Serverless E-Commerce Platform",
  "source_url": "https://aws.amazon.com/architecture/...",  // unique
  "description": "Short parsed summary of what this architecture does.",
  "use_cases": ["ecommerce", "web_application"],  // values from UseCase enum
  "aws_services": [
    {
      "name": "Amazon API Gateway",
      "category": "networking",        // compute | storage | database | networking |
                                       // analytics | integration | ml | security | other
      "purpose": "Routes and throttles client API traffic"
    }
  ],
  // Mirrors the 9 recommendation request dimensions so matching is a direct
  // field-for-field comparison. Populated by the parser (rules or LLM).
  "characteristics": {
    "use_cases": ["ecommerce", "web_application"],
    "scale": ["small", "medium"],                 // scales this design suits
    "traffic_patterns": ["bursty", "spiky"],
    "latency_sensitivity": "medium",              // max sensitivity it serves well
    "processing_styles": ["request_response", "event_driven"],
    "data_intensity": "medium",
    "availability": "high",                       // standard | high | critical
    "ops_model": "managed_services",              // managed_services | balanced | self_managed_ok
    "cost_profile": "medium"                      // low | medium | high (relative cost)
  },
  "diagram_url": "https://.../diagram.png",       // nullable
  "tags": ["serverless", "lambda", "dynamodb"],
  "scraped_at": ISODate,        // when raw content was fetched
  "parsed_at": ISODate,         // when parsing/extraction completed
  "parser_version": "rules-v1"  // or "llm-claude-sonnet-5-v1" — enables re-parsing
}
```

**Indexes:**

| Index | Type | Why |
|---|---|---|
| `slug` | unique | Stable public identifier for detail lookups |
| `source_url` | unique | Idempotent scraping — re-scrape upserts, never duplicates |
| `scraped_at` (desc) | single | List view sorted by recency |
| `characteristics.use_cases` | multikey | Pre-filter recommendation candidates |
| `tags` | multikey | Tag filtering in the list endpoint |

### 5.2 `scrape_jobs`

One document per triggered scrape run (audit trail + status polling for the frontend).

```jsonc
{
  "_id": ObjectId,
  "status": "completed",        // pending | running | completed | failed
  "trigger_source": "api",      // api | seed | manual
  "stats": {
    "pages_found": 25,
    "parsed_ok": 23,
    "failed": 2
  },
  "errors": [                    // per-page failures; job still completes
    { "url": "https://...", "reason": "timeout after 3 retries" }
  ],
  "started_at": ISODate,
  "finished_at": ISODate         // null while running
}
```

**Indexes:** `started_at` (desc) for job-history listing; `status` for polling queries.

**Data rules:**
- Upsert architectures by `source_url` — scraping is **idempotent**.
- All timestamps are UTC (`datetime.now(timezone.utc)`).
- Enum values are stored as their string values; validated by Pydantic on read and write.

---

## 6. API Contract

Base path: `/api/v1`. All responses JSON; errors use the envelope in §3.5.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/architectures` | Paginated list (`limit`, `offset`, optional `use_case`, `tag` filters). Returns summaries + timestamps + metadata |
| `GET` | `/architectures/{slug}` | Full architecture detail |
| `POST` | `/scrape` | Trigger a scrape job (runs as background task); returns `202` with `job_id` |
| `GET` | `/scrape/jobs/{job_id}` | Job status + stats (frontend polls this) |
| `GET` | `/scrape/jobs` | Recent job history |
| `POST` | `/recommendations` | Body: the 9-field requirements object → ranked recommendations |
| `GET` | `/health` | Liveness + Mongo ping (used by Docker healthcheck) |

### 6.1 Recommendation Request (all 9 fields required)

```json
{
  "use_case": "web_application | public_api | ecommerce | real_time_analytics | batch_processing | event_processing | media_delivery | internal_tool | iot_ingestion | ml_inference",
  "scale": "small | medium | large",
  "traffic_pattern": "steady | bursty | spiky | scheduled | unpredictable",
  "latency_sensitivity": "low | medium | high",
  "processing_style": "request_response | event_driven | batch | streaming",
  "data_intensity": "low | medium | high",
  "availability_requirement": "standard | high | critical",
  "ops_preference": "managed_services | balanced | self_managed_ok",
  "budget_sensitivity": "low | medium | high"
}
```

Enums are enforced with Pydantic `StrEnum`s. *(Assignment bonus: optionally accept free
strings and normalize them to the nearest enum — if implemented, this is a separate
normalization step in front of the same engine, never a change to the engine itself.)*

### 6.2 Recommendation Response

```json
{
  "recommendations": [
    {
      "architecture": { "...summary + metadata..." },
      "score": 0.87,
      "explanation": "Strong fit: designed for ecommerce with bursty traffic and managed services. Partial fit on scale (targets small–medium).",
      "match_breakdown": {
        "use_case": 1.0,
        "scale": 0.5,
        "traffic_pattern": 1.0
        // ... all 9 dimensions
      }
    }
  ],
  "total_candidates_evaluated": 23
}
```

### 6.3 Recommendation Engine Rules

- **Deterministic weighted scoring** — same input always yields the same output. The LLM
  is allowed in *parsing/enrichment* only, **never** in scoring.
- Per-dimension compatibility: exact match = 1.0; "adjacent" values earn partial credit
  via explicit O(1) lookup matrices (e.g., requested `scale=medium` vs supported
  `["small","medium"]` → 1.0; vs `["large"]` → 0.4). Matrices live in
  `services/recommendation/compatibility.py` with unit tests.
- Dimension weights (e.g., `use_case` weighted highest) are named constants in one place.
- Final score = weighted sum normalized to [0, 1]. Return top 3 (configurable), sorted
  descending; ties broken by most recently `parsed_at`.
- The explanation string is **generated from the breakdown** (template-based), so it can
  never contradict the score.
- Every scoring rule must have a unit test. The engine is pure (no I/O) — it takes
  requirements + candidate list and returns ranked results.

---

## 7. Task Tracking (Strict Rule)

**All task tracking and progress updates are done exclusively in [`todo.md`](todo.md).**

- `todo.md` contains the full User Stories / Sprint Breakdown and the Progress Checklist.
  It is the **only** file where tasks are defined, checked off, or updated.
- **Never** add stories, checklists, TODO lists, or progress notes to CLAUDE.md, the
  README, code comments, or anywhere else — CLAUDE.md holds rules and conventions only.
- Update the checklist in `todo.md` in the same commit that completes a story.
- If scope changes (a story is added, split, or dropped), record that change in `todo.md`
  and note the reason there.

---

## 8. Working Agreements for Agent Sessions

1. **Read this file first** in every session, then check [`todo.md`](todo.md) for current
   progress and [`MEMORY.md`](MEMORY.md) for past decisions and known pitfalls; follow
   the story order in `todo.md` unless told otherwise.
2. **Work one story at a time.** Complete it to its Definition of Done before starting
   the next. Do not scaffold ahead of the current story.
3. **Before every commit:** run backend `ruff check && ruff format --check && mypy &&
   pytest` and/or frontend `npm run lint && npm run build && npm test` for whatever was
   touched. A failing check blocks the commit — fix it, don't skip it.
4. **Update the progress checklist in `todo.md`** as part of the completing commit (§7).
5. **Secrets:** never commit `.env` or API keys; every new env var is added to
   `.env.example` with a comment. The app must run with **no** Claude API key (fallback
   parser).
6. **Keep the README current** — if a story changes setup or run instructions, updating
   the README is part of that story.
7. **Deviations:** if a requirement here conflicts with something discovered during
   implementation, state the conflict and the recommendation in your response — do not
   silently diverge from this document. If the owner approves a change, update CLAUDE.md
   in the same commit (`docs(repo): ...`).
8. **Memory (strict):** Before ending a session, if you encountered and fixed a complex
   bug or made an architectural decision, you MUST document it in
   [`MEMORY.md`](MEMORY.md) so future agents do not repeat the mistake. Use the entry
   format defined at the top of that file. This is a completion requirement, not a
   suggestion — decisions and fixes that live only in a chat transcript are lost.
