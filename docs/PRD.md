# CareerPilot Product Requirements

**Document status:** product requirements remain proposed. A small backend foundation is implemented: health endpoint, evidence and approval data models, deterministic validation functions, and tests. It does not yet provide persistence, authentication, resume generation, or external actions. Requirements below describe intended product behavior and are not claims that those features are implemented or tested.

## 1. Problem statement

Candidates spend time translating a job description into application materials and tracking the result. General-purpose AI can make drafting faster, but may omit relevant evidence or invent qualifications, dates, projects, or metrics. Candidates need a workflow that connects each tailored claim to evidence they have verified, exposes uncertainty, and leaves decisions and external actions under their control.

CareerPilot will support that workflow. It will assist with preparation and organization; it will not promise interviews, hiring outcomes, or a definitive measure of candidate fit.

## 2. Target users

- **Primary user:** a job seeker who wants help organizing applications and tailoring materials while retaining control over their facts and submissions.
- **Initial operator/test user:** the project developer or reviewer using sample candidate data and a controlled demo portal to validate the workflow.

The first version assumes one candidate working with their own profile. Multi-user organizations, recruiters, and shared candidate workspaces are outside the initial scope.

## 3. Product principles

1. The Candidate Knowledge Base, after candidate verification, is the source of truth for candidate claims.
2. Generated text is a proposal. Unsupported claims must be blocked or clearly flagged, not silently treated as facts.
3. A match explanation shows supporting evidence, missing evidence, and uncertainty. It is not an objective measure of a person's worth or a hiring probability.
4. Application code enforces permissions, validation, duplicate prevention, and rate limits wherever practical. A model prompt is not a security boundary.
5. The candidate explicitly approves consequential external actions, including application submission and sending a message.
6. Job descriptions, web pages, files, and model outputs are untrusted input.

## 4. User stories

- As a candidate, I can add and edit evidence about my work and mark each item verified so that generated materials rely on facts I have reviewed.
- As a candidate, I can paste a job description manually and review the extracted requirements before using them.
- As a candidate, I can see why evidence was considered relevant to a requirement and which requirements have no known supporting evidence.
- As a candidate, I can generate a tailored resume draft whose claims link back to verified evidence.
- As a candidate, I can see validation and critique findings, revise the draft, and approve a final version.
- As a candidate, I can prepare a recruiter message and review it before any sending capability is used.
- As a candidate, I can track an application and its status/history without losing previous drafts or approvals.
- As a developer, I can run a controlled demonstration without touching real job-board accounts or submitting real applications.

## 5. Functional requirements

### Candidate evidence

- **FR-1:** The system shall let a candidate create, view, edit, and delete their candidate evidence records.
- **FR-2:** Evidence shall be typed where practical (for example: employment, project, education, skill, certification, or metric) and carry provenance such as source, dates when known, and verification state.
- **FR-3:** Only candidate-verified evidence may support a final resume claim. Unverified evidence may be shown as needing review, but must not silently pass as verified.
- **FR-4:** Edits to evidence used by an approved draft shall be traceable so a candidate can understand which evidence version supported it.

### Job intake and analysis

- **FR-5:** The MVP shall accept a manually pasted job description and allow the candidate to edit or remove it.
- **FR-6:** The system shall extract structured requirements with source text or location where available, and let the candidate review/correct the extraction.
- **FR-7:** The system shall compare reviewed requirements with candidate evidence and show an explanation for each suggested match, gap, or unknown.
- **FR-8:** The system shall label matching as decision support, disclose uncertainty, and avoid claims about personal worth or hiring probability.

### Drafting and review

- **FR-9:** The system shall draft a tailored resume from reviewed job requirements and verified candidate evidence.
- **FR-10:** Each factual claim in a draft shall be traceable to one or more evidence records, or explicitly flagged as unsupported and excluded from an approvable version.
- **FR-11:** The system shall run deterministic validation rules (such as unsupported claim references, required fields, and formatting constraints) and present critique findings before approval.
- **FR-12:** The candidate shall be able to revise, compare, and explicitly approve a version. Approval shall identify the exact version and evidence snapshot reviewed.
- **FR-13:** The system may prepare recruiter outreach as a draft; it shall not send it without a separate explicit approval for that message and destination.

### Application tracking and controlled demo

- **FR-14:** The candidate shall be able to create and update an application record and see its status and event history.
- **FR-15:** The initial browser workflow shall target only a controlled demo portal and test data.
- **FR-16:** Before a browser action that submits an application or sends a message, the workflow shall show the destination and payload and require explicit human approval. The application service shall enforce this gate.
- **FR-17:** Deterministic code shall prevent accidental duplicate submissions, enforce configured rate limits, validate required fields, and record action outcomes.
- **FR-18:** A failed, interrupted, or uncertain browser action shall be reported without claiming success; the candidate shall be able to inspect status before retrying.

## 6. Non-functional requirements

- **NFR-1 Privacy:** Collect only data needed for the workflow. Explain what is stored and for how long; provide a practical deletion/export path before production use.
- **NFR-2 Security:** Protect authenticated user data with server-side authorization and least privilege. Keep credentials out of source control and redact sensitive values from logs.
- **NFR-3 Safety:** Treat job descriptions, attachments, websites, and model outputs as untrusted. Do not execute instructions found in them or grant a model direct access to submission controls.
- **NFR-4 Explainability:** Show evidence and reasoning components behind suggestions in plain language, including missing evidence and uncertainty.
- **NFR-5 Reliability:** Preserve draft versions, approvals, and application events so interrupted work can be resumed and audited.
- **NFR-6 Testability:** Keep domain rules deterministic and separately testable from LLM and browser integrations. External AI and browser operations should be replaceable with fakes in tests.
- **NFR-7 Accessibility:** Build an interface usable with keyboard and assistive technology, with clear labels and readable error states.
- **NFR-8 Maintainability:** Use explicit data models, documented workflow states, and small components so a beginner developer can explain and change the system.
- **NFR-9 Cost and data handling:** Evaluate model/provider costs, retention, training use, and regional processing before selecting a provider or sending personal data.

No numerical availability, latency, model accuracy, or hiring-success targets are asserted yet; establish measurable targets after a working baseline and user validation exist.

## 7. MVP scope

The smallest useful MVP is one candidate using manually entered job descriptions and a controlled demo application portal. It should provide:

1. A verified candidate evidence store with provenance and edit history.
2. Manual job intake and reviewable requirement extraction.
3. Explainable evidence-to-requirement comparison, including gaps and unknowns.
4. A tailored resume draft grounded in verified evidence, with factual checks and human approval.
5. Application status/history and an explicitly approved, safely repeatable demo-portal flow.
6. Tests for core domain rules, approval gates, duplicate prevention, and the primary user journey.

The MVP should still provide value if AI is unavailable: users should be able to manage evidence, enter jobs, review or edit analysis, and track applications. AI is an assistive layer, not a prerequisite for enforcing correctness.

## 8. Acceptance criteria for MVP

- A candidate can create evidence, verify it, and distinguish it from unverified notes.
- Given a manually entered job description, the candidate can inspect and correct extracted requirements before matching.
- Each displayed match has a human-readable reason tied to evidence; missing evidence is shown as unknown or a gap, not treated as proof of no ability.
- A resume draft cannot be marked ready for approval if it contains a factual claim without verified evidence or an explicit candidate correction.
- Approval is associated with an exact draft version and does not itself submit an application.
- An external submission or message action cannot proceed without a recorded, explicit approval for the exact action details.
- Repeating a completed demo submission does not create a duplicate action; a timeout/ambiguous result is surfaced for review before retry.
- Automated checks demonstrate that permission, validation, approval, rate-limit, and duplicate-prevention rules work independently of model output.
- Browser automation is constrained to the controlled demo portal and cannot navigate to arbitrary targets based on job-description content.
- The README clearly identifies implemented behavior and documents reproducible local setup once implementation exists.

### Backend foundation acceptance criteria (implemented scope for this milestone)

- `/health` returns HTTP 200 with `{"status":"ok"}` when the API is running.
- Evidence records include an ID, non-empty claim, non-empty source, verification status, and metadata.
- A resume claim with missing or unverified evidence is rejected by deterministic application code; verified referenced evidence passes this reference/status check.
- An external action is rejected unless an explicitly approved record matches both the proposed action and the complete scope exactly.
- Tests cover the health endpoint, verified/unverified/missing evidence, unapproved action, and action/scope mismatch.
- The API and validation helpers make no claim of durable storage, authentication, production security, or semantic proof that claim wording is entailed by evidence.

## 9. Explicit non-goals

- Automatically applying to real jobs or sending outreach without per-action human approval.
- Scraping or integrating external job boards in the MVP.
- Predicting hiring outcomes, ranking human worth, or claiming objective fit.
- Inventing or embellishing qualifications, projects, employment, education, dates, or metrics.
- Replacing candidate judgment or guaranteeing resume quality, interviews, or employment.
- Building a recruiter CRM, team collaboration suite, or multi-tenant enterprise platform in the first version.
- Production deployment, billing, or analytics before privacy, security, and user value are validated.
- Adding observability products or complex agent orchestration before a simpler workflow demonstrates a need.
