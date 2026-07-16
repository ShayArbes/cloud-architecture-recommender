# MEMORY.md — Long-Term Agent Memory

> **Purpose:** Persistent, cross-session memory for all agents on this project.
> Rules live in `CLAUDE.md`, task state lives in `todo.md`, and **hard-won knowledge
> lives here**. Per CLAUDE.md §8: before ending a session, if you encountered and fixed
> a complex bug or made an architectural decision, you MUST document it here so future
> agents do not repeat the mistake.

**Entry format:** newest entries first within each section, each entry as:

```
### YYYY-MM-DD — <short title> (<agent role>)
**Context:** what was happening
**Decision / Fix:** what was decided or done
**Why / Lesson:** the reasoning, and what a future agent must know
```

---

## 1. Architectural Decisions

### 2026-07-16 — Recommendation scoring is deterministic; LLM allowed only for parsing (Architect)
**Context:** The assignment encourages using AI creatively; it was tempting to have an LLM produce recommendations.
**Decision / Fix:** The recommendation engine is a pure, deterministic weighted-scoring function (CLAUDE.md §6.3). The Claude API may be used only in the scraping/parsing stage, behind the `ArchitectureParser` protocol, with a rule-based fallback so the app runs with no API key.
**Why / Lesson:** Deterministic scoring is unit-testable, reproducible for graders, free, and explainable. Never route scoring through an LLM; never make the API key a hard dependency.

### 2026-07-16 — Architectures store a `characteristics` object mirroring the 9 request dimensions (Architect)
**Context:** Needed a matching strategy between free-form scraped content and the strict 9-field recommendation request.
**Decision / Fix:** Parsing normalizes every architecture into a `characteristics` object with the same 9 dimensions as the request (CLAUDE.md §5.1), so matching is a direct field-for-field comparison in O(n·f).
**Why / Lesson:** Do the hard normalization work once at parse time, not on every recommendation request. Any new matching dimension must be added to the request schema, the characteristics schema, and the compatibility matrices together.

### 2026-07-16 — Rules, state, and memory are three separate files (Architect)
**Context:** CLAUDE.md originally mixed conventions with sprint stories and the progress checklist.
**Decision / Fix:** `CLAUDE.md` = rules/conventions only; `todo.md` = user stories + progress checklist (exclusive home of task tracking, CLAUDE.md §7); `MEMORY.md` = decisions, resolved bugs, and lessons.
**Why / Lesson:** Keeps each file authoritative for one concern. Never write progress notes here or in CLAUDE.md — check boxes in `todo.md`; never write rules here — propose them for CLAUDE.md.

### 2026-07-16 — Multi-agent ownership boundaries defined in `.agents/` (Architect)
**Context:** Multiple agent roles will work on the repo; overlapping edits cause conflicts and layering violations.
**Decision / Fix:** Five role files in `.agents/` define per-role directory ownership. Notable seams: `backend/app/repositories/` is co-owned by Data Engineer + Backend; `.env.example` is owned solely by DevOps (others request additions).
**Why / Lesson:** Before editing any path, confirm your role owns it. Cross-boundary needs are requests to the owning agent, not direct edits.

## 2. Resolved Bugs & Pitfalls

### 2026-07-17 — Motor's `AsyncIOMotorClient` is generic; mypy --strict rejects bare usage (Backend)
**Context:** S0.2 — `mypy --strict` failed with `type-arg` / `no-any-return` errors on every bare `AsyncIOMotorClient` annotation, and `request.app.state.mongo_client` is typed `Any`.
**Decision / Fix:** Single alias `MongoClient = AsyncIOMotorClient[dict[str, Any]]` in `app/db/client.py`; all layers import it. `get_mongo_client` casts `app.state.mongo_client` to it.
**Why / Lesson:** Always annotate Motor clients/collections with the `dict[str, Any]` document type parameter via the shared alias — never bare. Repositories (S1.4+) must reuse this alias, not redefine it.

### 2026-07-17 — Vite `react-ts` template no longer matches project rules out of the box (Frontend)
**Context:** S0.3 — current `npm create vite` (Vite 8) ships **oxlint** instead of ESLint and omits `"strict"` from `tsconfig.app.json`.
**Decision / Fix:** Replaced oxlint with ESLint (typescript-eslint `strictTypeChecked` + react-hooks + prettier config) and added `strict` + `noUncheckedIndexedAccess` to `tsconfig.app.json`. `npm run lint` runs both eslint and `prettier --check`.
**Why / Lesson:** Do not assume the scaffold satisfies CLAUDE.md §2/§3.4 — verify lint/strictness config after any template upgrade.

### 2026-07-17 — Port 27017 on this dev machine is taken by a local MongoDB Windows service (DevOps)
**Context:** S0.4 — the compose mongo container could not bind 27017 because a locally installed MongoDB service already listens there; a backend "connected" health check may be talking to the *local* service, not the container.
**Decision / Fix:** Host port is configurable: `${MONGO_HOST_PORT:-27017}` in `docker-compose.yml` (documented in `.env.example`). Verification used port 27018 to guarantee the container was the responder.
**Why / Lesson:** When verifying Mongo connectivity on this machine, use a non-default host port (e.g. 27018) or you cannot tell the container apart from the local service.

## 3. Workflow Lessons

### 2026-07-16 — Update `todo.md` in the same commit that completes a story (Architect)
**Context:** Progress tracking drifts when check-offs are batched "later."
**Decision / Fix:** The checklist tick is part of the story's Definition of Done and belongs in the completing commit (CLAUDE.md §7).
**Why / Lesson:** `todo.md` is only trustworthy if it is never allowed to lag the code.
