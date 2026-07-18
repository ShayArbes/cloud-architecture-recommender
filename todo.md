# todo.md — User Stories & Progress Tracking

> **This file is the single source of truth for project state.** All task tracking and
> progress updates happen here — never in `CLAUDE.md`. Architecture rules and conventions
> live in `CLAUDE.md`; read it before starting any story.

---

## 1. User Stories / Sprint Breakdown

Stories are small and independently completable. Each has acceptance criteria (AC).
**Definition of Done (applies to every story):** code + tests written and passing,
linters/type-checkers clean, story committed atomically with Conventional Commits,
progress checklist (§2 below) updated.

### Sprint 0 — Repository & Tooling Foundation
- **S0.1 — Repo scaffolding:** Monorepo layout from CLAUDE.md §1; `.gitignore` (Python,
  Node, Docker, IDE, `.env`); `.env.example`; README skeleton.
  *AC: tree matches CLAUDE.md §1; no generated files tracked.*
- **S0.2 — Backend skeleton:** FastAPI app factory, `pydantic-settings` config, logging
  setup, `/health` endpoint, Ruff/mypy/pytest configured in `pyproject.toml`.
  *AC: `uvicorn app.main:app` serves `/health`; `ruff check`, `mypy`, `pytest` all pass.*
- **S0.3 — Frontend skeleton:** Vite + React + TS strict, ESLint/Prettier, app shell
  with routing/navigation placeholders.
  *AC: `npm run build` and `npm run lint` pass.*
- **S0.4 — Compose skeleton:** `docker-compose.yml` with MongoDB service + named volume;
  backend connects to it locally via env vars.
  *AC: `docker compose up mongo` works; backend `/health` reports Mongo connectivity.*

### Sprint 1 — Scraping & Parsing Module
- **S1.1 — Fetcher:** Async httpx client to discover and download AWS architecture pages;
  timeouts, retry w/ backoff, polite rate-limiting.
  *AC: returns raw HTML for N architecture pages; failures logged, not fatal.*
- **S1.2 — Rule-based parser:** `ArchitectureParser` protocol + BeautifulSoup
  implementation extracting title, description, AWS services, diagram URL, tags.
  *AC: unit-tested against saved HTML fixtures (no network in tests).*
- **S1.3 — Characteristics extraction:** Derive the 9-dimension `characteristics` object
  (keyword/service-based heuristics); optional Claude-API parser behind the same protocol.
  *AC: every stored architecture has a complete, enum-valid characteristics object;
  works with no API key present.*
- **S1.4 — Persistence:** Repository upserting by `source_url`; index creation at startup;
  `scrape_jobs` lifecycle records.
  *AC: re-running the scrape produces zero duplicates; job stats accurate.*

### Sprint 2 — Backend API
- **S2.1 — List endpoint:** `GET /architectures` with pagination + filters.
  *AC: paginated, sorted by `scraped_at` desc; response schema documented in OpenAPI.*
- **S2.2 — Detail endpoint:** `GET /architectures/{slug}`.
  *AC: 200 with full document; 404 envelope for unknown slug.*
- **S2.3 — Trigger scrape:** `POST /scrape` running the Sprint 1 pipeline as a background
  task; `GET /scrape/jobs/{id}` + job history endpoint.
  *AC: returns 202 immediately; job status transitions pending→running→completed/failed;
  concurrent duplicate jobs are rejected with 409.*
- **S2.4 — API integration tests:** httpx `AsyncClient` tests against a test database.
  *AC: happy path + error path covered for every endpoint.*

### Sprint 3 — Recommendation Engine
- **S3.1 — Request schema:** Pydantic model with the 9 required enum fields (CLAUDE.md §6.1).
  *AC: missing/invalid field → 422 with field-level detail.*
- **S3.2 — Scoring engine:** Compatibility matrices + weighted scorer as a pure service.
  *AC: unit tests cover exact / partial / no match per dimension; O(n·f) single pass.*
- **S3.3 — Explanations:** Template-based explanation from the match breakdown.
  *AC: explanation names the strongest and weakest dimensions; consistent with scores.*
- **S3.4 — Endpoint:** `POST /recommendations` wiring schema → engine → response
  (CLAUDE.md §6.2).
  *AC: returns top 3 ranked; empty inventory returns an explicit empty result, not an error.*

### Sprint 4 — Frontend
- **S4.1 — API layer:** Typed client + React Query hooks for all endpoints.
  *AC: types mirror backend schemas; no `any`.*
- **S4.2 — Architecture list page:** Paginated list with timestamps + metadata.
  *AC: loading/error/empty/success states all rendered.*
- **S4.3 — Architecture detail view:** Full details — services, characteristics, diagram, tags.
  *AC: reachable from list; unknown slug shows friendly not-found.*
- **S4.4 — Scrape trigger UI:** Button + job status (polling `scrape/jobs/{id}`), disabled
  while a job is running.
  *AC: user sees live pending→running→completed transition and result stats.*
- **S4.5 — Recommendation form + results:** Typed form for the 9 fields (selects from
  shared enum constants) + ranked results with scores and explanations.
  *AC: client-side required validation; results show score, explanation, link to detail.*

### Sprint 5 — DevOps & Polish
- **S5.1 — Dockerfiles:** Multi-stage builds for backend (slim Python) and frontend
  (build → nginx serve); non-root users.
  *AC: both images build and run standalone.*
- **S5.2 — Compose orchestration:** Full `docker-compose.yml` — mongo + backend +
  frontend, healthchecks, dependency ordering, env via `.env`.
  *AC: `docker compose up --build` from a clean clone yields a fully working app.*
- **S5.3 — Seed data:** Seed script/fixture so the app is demonstrable immediately even
  if live scraping is blocked.
  *AC: fresh environment shows architectures and returns recommendations.*
- **S5.4 — README:** Setup + run instructions (Compose), architecture explanation,
  API documentation pointer, design decisions & trade-offs.
  *AC: a new developer can run everything from the README alone.*
- **S5.5 — Final QA:** Full pass of linters, type checks, tests; manual end-to-end walk
  of every frontend flow; Git history review (atomic, conventional).
  *AC: checklist below 100% complete.*

---

## 2. Progress Checklist

> **Agents must update this checklist in the same commit that completes a story**
> (`docs(repo): check off S2.1 in progress checklist` may be folded into the story commit).

### Sprint 0 — Foundation
- [x] S0.1 Repo scaffolding (`.gitignore`, `.env.example`, layout, README skeleton)
- [x] S0.2 Backend skeleton (FastAPI factory, config, logging, `/health`, tooling)
- [x] S0.3 Frontend skeleton (Vite + React + TS strict, lint, app shell)
- [x] S0.4 Compose skeleton (MongoDB service, backend connectivity)

### Sprint 1 — Scraping & Parsing
- [x] S1.1 Async fetcher (retries, backoff, rate limiting)
- [x] S1.2 Rule-based parser (+ HTML fixtures & tests)
- [x] S1.3 Characteristics extraction (heuristics; optional LLM parser; no-key fallback)
- [x] S1.4 Idempotent persistence + scrape job records + indexes

### Sprint 2 — Backend API
- [x] S2.1 `GET /architectures` (pagination, filters)
- [x] S2.2 `GET /architectures/{slug}`
- [ ] S2.3 `POST /scrape` + job status endpoints
- [ ] S2.4 API integration tests

### Sprint 3 — Recommendation Engine
- [ ] S3.1 Request schema (9 enum fields, 422 handling)
- [ ] S3.2 Weighted scoring engine (+ unit tests)
- [ ] S3.3 Explanation generation
- [ ] S3.4 `POST /recommendations` endpoint

### Sprint 4 — Frontend
- [ ] S4.1 Typed API layer + React Query hooks
- [ ] S4.2 Architecture list page
- [ ] S4.3 Architecture detail view
- [ ] S4.4 Scrape trigger + job status UI
- [ ] S4.5 Recommendation form + results view

### Sprint 5 — DevOps & Polish
- [ ] S5.1 Dockerfiles (backend, frontend)
- [ ] S5.2 docker-compose.yml (mongo + backend + frontend, healthchecks)
- [ ] S5.3 Seed data
- [ ] S5.4 Comprehensive README
- [ ] S5.5 Final QA (lint, types, tests, e2e walkthrough, Git history review)
