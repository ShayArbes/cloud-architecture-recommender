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

*(No entries yet — no application code exists. First agent to fix a non-trivial bug adds it here.)*

## 3. Workflow Lessons

### 2026-07-16 — Update `todo.md` in the same commit that completes a story (Architect)
**Context:** Progress tracking drifts when check-offs are batched "later."
**Decision / Fix:** The checklist tick is part of the story's Definition of Done and belongs in the completing commit (CLAUDE.md §7).
**Why / Lesson:** `todo.md` is only trustworthy if it is never allowed to lag the code.
