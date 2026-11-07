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

**Status: early backend foundation.** The FastAPI backend has a public health endpoint and Supabase-authenticated evidence API backed by a local SQLite database. It verifies access tokens, maps their Supabase user ID to `candidate_id`, and rejects mismatches. Action approval remains an in-memory validation helper; resume generation and external-action endpoints are not implemented. This is a learning foundation and has not had a production security review. All other capabilities remain planned unless explicitly labeled otherwise.

## Run the backend locally

Python 3.11 or newer is required. From the repository root, install the backend and its test dependencies, then start the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e "./backend[dev]"
if [ ! -f .env ]; then cp .env.example .env; fi
# Edit .env and set the Supabase project URL and publishable key.
uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is `http://127.0.0.1:8000/health`. In a second terminal, activate the same environment and run the backend tests:

```bash
source .venv/bin/activate
python -m pytest backend/tests
```

Auth tests use generated signing keys and mocked network responses. They do not need live Supabase credentials or network access.

Evidence is stored in `backend/data/careerpilot.sqlite3` by default. Set `CAREERPILOT_DB_PATH` to choose another SQLite file; a relative value is resolved from the repository root, regardless of the server's launch directory. An empty value is rejected during backend startup. On POSIX systems, a newly created database file is created with owner-only permissions. Existing database file permissions are left unchanged. SQLite may create journal/sidecar files; this project does not set or verify their permissions. The database is local and is not encrypted or backed up by this project, so filesystem access controls and local device security still matter.

The root `.env` is ignored by Git. The backend loads it locally without printing its values; process environment variables take precedence. Copy the project URL and publishable key from the Supabase dashboard's API settings. The browser/client must obtain an **access token for a signed-in Supabase user** and send `Authorization: Bearer <access-token>` to evidence routes. This backend does not implement login or issue user tokens.

For a manual setup, use a Supabase project with Auth enabled, copy its Project URL and publishable key into `.env`, then sign in a test user through a Supabase client to obtain a session access token. The backend verifies RS256/ES256 signatures with the project's public JWKS and checks the issuer, audience, expiry, authenticated role, and user ID. For `HS256`, it asks the project's `/auth/v1/user` endpoint to validate the bearer token and sends the publishable key separately in the `apikey` header. The publishable key identifies the project for API access; it is not a user's session and is never accepted as the bearer credential. You do not need to copy a signing secret into this repository. See [Supabase JWT guidance](https://supabase.com/docs/guides/auth/jwts) and [JWT signing keys](https://supabase.com/docs/guides/auth/signing-keys).

Candidate ownership maps directly to the Supabase `auth.users.id`: the authenticated JWT `sub` must equal the `candidate_id` in the route. A different candidate ID returns 403. The API still does not provide login, user registration, refresh-token management, or a production security review. Existing SQLite rows are reachable only if their stored candidate ID already matches the user's Supabase UUID; back up and deliberately migrate any data before using those accounts.

Available evidence routes are `POST /candidates/{candidate_id}/evidence`, `GET /candidates/{candidate_id}/evidence`, `GET /candidates/{candidate_id}/evidence/{evidence_id}`, and `PATCH /candidates/{candidate_id}/evidence/{evidence_id}/verification`. New evidence starts unverified. The verification update changes only its status and update timestamp, preserving its claim and source metadata.

The proposed future local stack may include a frontend and a larger database such as PostgreSQL, but neither is implemented or needed to run this backend foundation.

For the product requirements, see [docs/PRD.md](docs/PRD.md). For the proposed system design, see [docs/architecture.md](docs/architecture.md). For dependency-ordered implementation steps, see [docs/roadmap.md](docs/roadmap.md).
