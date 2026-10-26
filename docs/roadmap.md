# CareerPilot Roadmap

**Status:** proposed sequence. Milestones are ordered by dependency and have no artificial deadline. A milestone is complete only when its deliverable can be demonstrated and its stated validation has passed; planned work must not be described as implemented beforehand.

## Current project state

The documentation foundation and the first backend slice exist. The backend currently has a health endpoint, in-memory Pydantic evidence and action-approval models, deterministic evidence-reference/verification and exact action/scope checks, and pytest coverage. Persistence, authentication, CRUD APIs, resume drafting, and external action execution are not implemented. The API is not production-secure.

## Milestone 0 — Product and repository foundation

**Deliverables**

- Product scope and safety principles documented.
- Initial architecture, trust boundaries, and dependency-aware roadmap documented.
- Project status accurately recorded as documentation-only until code exists.

**Dependencies:** none.

**Validation steps**

- Review that MVP starts with manual job descriptions and a controlled demo portal.
- Check that every external action has an explicit human approval gate.
- Check that candidate facts are grounded in verified evidence and that the match is not framed as worth or hiring probability.

**Definition of done:** the documentation is internally consistent, names unresolved choices, and does not claim unimplemented functionality as complete.

## Milestone 1 — Runnable project skeleton and deterministic domain model

**Deliverables**

- Minimal Next.js/TypeScript UI and FastAPI/Python service, if the proposed split is still justified.
- Reproducible local developer instructions; Docker Compose for PostgreSQL if it reduces setup friction.
- Initial schema and domain rules for candidate evidence, verification, jobs, and application states.
- CI workflow running formatting/type checks and a small test suite.

**Dependencies:** Milestone 0; confirm framework and runtime versions when scaffolding.

**Validation steps**

- A new developer follows the documented setup on a clean checkout.
- Backend tests verify evidence ownership, verification transitions, and allowed state changes.
- No secrets are committed; example configuration contains placeholders only.

**Definition of done:** the project runs locally with a documented health check, core domain rules are tested without AI, and the README distinguishes working setup from future features.

**Progress:** The minimal backend foundation is in place, including local run instructions and unit/API tests. The larger milestone remains in progress: no frontend, database, authentication, persistence, or CI workflow has been added.

## Milestone 2 — Candidate Knowledge Base

**Deliverables**

- Candidate evidence create/read/update/delete flow with types, provenance, verification state, and version history.
- Basic authentication/ownership boundary appropriate to the local MVP; decide how it will evolve before hosting.
- Candidate-facing evidence review UI.

**Dependencies:** Milestone 1.

**Validation steps**

- Verify users cannot access another candidate's records.
- Verify evidence edits create a traceable new version and do not silently rewrite evidence used by an existing draft.
- Verify unverified evidence remains visibly distinct.

**Definition of done:** a candidate can manage evidence and establish which records are verified; automated checks cover ownership and version behavior.

## Milestone 3 — Manual job intake and explainable analysis

**Deliverables**

- Manual job description entry and storage.
- Requirement extraction behind a replaceable AI interface, with schema validation and editable review screen.
- First evidence retrieval and match explanations; start with keyword/metadata retrieval.
- Explicit supported/partial/unknown/not-evidenced states and uncertainty language.

**Dependencies:** Milestone 2; select an AI provider only after privacy and data-handling review.

**Validation steps**

- Use synthetic job descriptions and candidate profiles, including injection-like instructions in job text.
- Confirm job content cannot change system rules or cause an external action.
- Have a reviewer inspect whether explanations point to the right evidence and make unknowns clear.
- Compare simple retrieval quality before considering embeddings or pgvector.

**Definition of done:** a user can enter a job, review/correct extracted requirements, and inspect evidence-backed explanations; tests show untrusted job text cannot bypass application rules.

## Milestone 4 — Evidence-grounded resume drafting and approval

**Deliverables**

- Resume draft generation using reviewed requirements and verified evidence only.
- Claim-to-evidence references and deterministic validation.
- Critique/revision flow and version comparison.
- Human approval tied to an exact draft and evidence snapshot.
- Optional recruiter message drafting, with its own review state.

**Dependencies:** Milestone 3; choose whether a simple state machine suffices or LangGraph is justified by pause/resume needs.

**Validation steps**

- Test that invented evidence IDs, unverified evidence, and unsupported factual claims cannot enter an approvable draft.
- Review outputs for omission and distortion using a small consented or synthetic evaluation set.
- Verify edits invalidate prior approval and that approved content is reproducible from stored versions.
- Measure quality against agreed review criteria before making claims about usefulness.

**Definition of done:** a candidate can produce, inspect, correct, validate, and approve a fact-grounded draft; application code blocks unsupported claims and records the reviewed version.

## Milestone 5 — Application tracking and controlled demo portal

**Deliverables**

- Application record, status changes, and event history.
- Controlled demo portal with test data and documented allowlisted origin/routes.
- Playwright runner isolated from model tools, with deterministic checks for approval, destination, fields, rate limit, and duplicate/idempotency key.
- Clear handling of confirmed, failed, and ambiguous browser outcomes.

**Dependencies:** Milestone 4; demo portal and safe test accounts must exist before browser automation is enabled.

**Validation steps**

- Run an end-to-end test only against the controlled portal.
- Verify no browser action occurs without action-specific approval for exact destination and payload.
- Verify repeated requests do not duplicate a completed action and ambiguous results require inspection.
- Verify unexpected origin, redirect, or page structure fails closed.

**Definition of done:** a complete demo application can be prepared, explicitly approved, executed against the controlled portal, and tracked; automated tests exercise approval and failure paths.

## Milestone 6 — MVP review and hardening

**Deliverables**

- Documented end-to-end local setup and known limitations.
- Privacy, retention, deletion/export, secret-handling, and threat-review decisions.
- Accessibility and usability fixes from candidate walkthroughs.
- Optional pgvector, LangGraph, or observability evaluation only where evidence supports the added complexity.

**Dependencies:** Milestones 1–5.

**Validation steps**

- Walk a beginner through setup and a complete synthetic-data journey.
- Review access controls, logs, AI data flow, prompt-injection handling, browser allowlists, and approval records.
- Confirm there are no real job-board destinations or credentials in demo configuration.
- Reassess documented feature status against actual tests and implementation.

**Definition of done:** MVP behavior is reproducible, core risks have documented controls or explicit limitations, and README status is accurate.

## Future work — only after MVP validation

- Real job-board integrations or imports, after policy, terms, privacy, reliability, and user authorization review.
- Additional document formats, calendar/reminder support, or application analytics if users demonstrate a need.
- Embedding-based retrieval and pgvector if measured retrieval quality improves materially over a simple baseline.
- LangGraph if the workflow needs durable resume points or branching that a small explicit state machine cannot handle.
- Langfuse/OpenTelemetry if concrete debugging/operations needs justify them and privacy controls are in place.
- Hosted multi-user deployment, account recovery, production security review, and operational monitoring.

These are possibilities, not commitments. The project should avoid building integrations or infrastructure before the core evidence-to-approved-draft workflow works reliably.
