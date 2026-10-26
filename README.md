# CareerPilot

CareerPilot is a planned agentic AI job-search and application assistant. It is intended to help a candidate understand a job description, compare it with verified evidence about their experience, prepare a tailored resume and recruiter outreach, and keep an application organized.

## The problem

Job applications take repeated research and careful writing. Tailoring can be useful, but it also creates a risk: a generated resume or message may state something the candidate has not actually done. CareerPilot is designed around a verified Candidate Knowledge Base and human review so that AI can help with analysis and drafting without becoming the source of truth or taking consequential actions on its own.

## Proposed workflow and features

The intended workflow is:

1. The candidate manually enters a job description.
2. CareerPilot extracts and presents role requirements for the candidate to review.
3. The system produces an explainable comparison against candidate evidence, including unknowns and gaps. This is not a measure of personal worth or a prediction of hiring success.
4. The system retrieves relevant, verified evidence and drafts a tailored resume and optional recruiter message.
5. Deterministic checks and a critique-and-revision step flag unsupported statements for correction.
6. The candidate reviews and explicitly approves any final document and any external action.
7. In the initial demo, a controlled demo portal can be used to rehearse an application, then record its status and history.

These are planned features, not implemented functionality. The initial MVP is intentionally limited to manually entered jobs and a controlled demo application portal. External job-board integrations are future work and are not part of the MVP.

## Proposed technology stack

| Technology | Intended purpose | Why it is proposed |
| --- | --- | --- |
| Next.js, TypeScript, Tailwind CSS | Candidate-facing web interface | Next.js provides a structured React application; TypeScript catches many data-shape mistakes during development; Tailwind is a proposed way to build consistent styling quickly. Confirm that a full-stack framework is appropriate when the UI scope is clearer. |
| Python, FastAPI | Backend API and domain services | Python has a broad AI/data ecosystem; FastAPI provides typed HTTP endpoints and request validation. Keep important business rules in ordinary application code rather than prompts. |
| PostgreSQL | Durable relational data store | It can represent users, verified evidence, jobs, drafts, approvals, and application history with clear relationships and transactions. |
| pgvector | Optional vector search over evidence | It may help retrieve semantically related candidate evidence. Validate that it improves retrieval over simpler keyword and metadata filtering before depending on it. |
| LangGraph | Explicitly modeled multi-step AI workflow | It may help represent resumable steps and human review checkpoints. Validate whether its added complexity is justified; deterministic workflow code may be enough initially. |
| LLM API and embeddings | Requirement extraction, drafting, critique, and semantic retrieval | These are proposed AI capabilities. Provider, model, data handling terms, cost, and quality must be evaluated before selection. Outputs remain untrusted drafts. |
| pytest and suitable frontend tests | Backend and UI behavior checks | Tests can protect validation rules, permissions, workflow transitions, and user-visible behavior as the project is implemented. |
| Playwright | Browser automation for the controlled demo portal | It can exercise a browser workflow end to end. Initially restrict it to a test portal with test data; do not automate real job boards. |
| Docker and GitHub Actions | Reproducible local services and automated checks | Docker can make the database and application environment easier to reproduce. GitHub Actions can run checks on changes. Exact deployment and CI setup are not yet selected. |
| Langfuse and OpenTelemetry (later, if justified) | AI trace inspection and application telemetry | Consider only when real workflow complexity makes tracing valuable. Define data minimization and redaction before recording prompts or outputs. |

This is a proposed stack, not a set of finalized implementation decisions. See [the architecture notes](docs/architecture.md) for decisions that need validation.

## Project status

**Status: early backend foundation.** The repository now has a FastAPI health endpoint, Pydantic models for candidate evidence and action approval, deterministic validation functions, and pytest tests. These are the only implemented product-related capabilities. They use in-memory objects and provide no persistence, authentication, resume generation, or external-action endpoint. This is a learning foundation, not a production-secure service. All other capabilities remain planned unless explicitly labeled otherwise.

## Run the backend locally

Python 3.11 or newer is required. From the repository root, install the backend and its test dependencies, then start the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e "./backend[dev]"
uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is `http://127.0.0.1:8000/health`. In a second terminal, activate the same environment and run the backend tests:

```bash
source .venv/bin/activate
python -m pytest backend/tests
```

The API currently stores no candidate or approval records, so the validation services receive in-memory model objects from their caller. Do not use this version with real candidate data or real applications. It has no authentication, database, or external-action integration. No API keys are needed for this foundation; never add secrets to source control.

The proposed future local stack may include a frontend and database, but neither is implemented or needed to run this backend foundation.

For the product requirements, see [docs/PRD.md](docs/PRD.md). For the proposed system design, see [docs/architecture.md](docs/architecture.md). For dependency-ordered implementation steps, see [docs/roadmap.md](docs/roadmap.md).
