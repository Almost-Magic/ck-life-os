# CK Life OS v1.0

**Five Practices for Living - No Gamification, No Pressure, No Comparison**

- **Port:** 5420
- **Status:** DONE_LOCAL_INTERNAL_REGISTERED_OPENROUTER_ROUTING_ENCRYPTED_JOURNAL_INNER_WORK_RAG_SOURCES_LIFE_MANAGER_V2_CALM_TABBED_LAYOUT for the approved local/internal scope
- **Tests:** Beast/FastAPI tests, smoke, route, gateway, browser QA, matrix, RAG source-draft/approved-fetch/search proof, and semantic map proof
- **Practices:** 5 universal practices: Presence, Reflection, Intention, Gratitude, Equanimity
- **Gamification:** Disabled structurally
- **Difficult Month Mode:** First-class feature
- **Runtime Independence:** Core local UI works without unrelated AMTL apps, providers, paid services, PostgreSQL, or scheduler

## Product Bible

CK Life OS is a calm personal practice OS. It helps a user record and reflect on five universal practices without pressure mechanics.

The app must never turn practice into performance. It should support a lived moment, not manufacture attention.

## Five Practices

1. **Presence** - Awareness, attention, showing up.
2. **Reflection** - Contemplation, processing, understanding.
3. **Intention** - Direction, values alignment, deliberate choices.
4. **Gratitude** - Appreciation, perspective, recognising good.
5. **Equanimity** - Balance, acceptance, steady perspective.

No philosophical tradition is named in the UI. These practices are presented in secular, accessible language.

## Non-Negotiables

- No streaks.
- No scores.
- No badges.
- No comparison view.
- Reflection prompts are offered after save, never pushed.
- A user can disable all prompts.
- Difficult Month Mode is visible and first-class.
- Unknown practices are rejected. Only the five canonical practices are valid.
- Synthetic data is labelled as synthetic data.
- Buttons and counts must have backend truth.

## Local/Internal Runtime

The delivered local/internal app includes:

- A calm product UI at `/`.
- Canonical five-practice validation on record and prompt routes.
- Local JSONL practice receipts stored outside the repo by default.
- Local encrypted journal stored outside the repo by default; journal title/content are encrypted at rest with Fernet and a server-side local key.
- Private Inner Work mode for shadow integration, observation/JK-style inquiry, grounding, relationship patterns, and unknown-mode reflection, stored encrypted at rest.
- 6W and ELI10 contextual guide drilldowns for every practice.
- Field-level helper text for each practice card.
- A 500-item local field/navigation innovation catalogue absorbed through the Innovation lens, not exposed as a raw register.
- Product Bible matrix, R2D2-equivalent, UI truth, data truth, dependency-status, and receipt proof endpoints.
- Guided-use, report/export, synthetic-data hygiene, OSS adoption truth, cost/effort-reduction truth, local handoff gate, delivery matrix, and semantic intent map artifacts.
- Dependency-down behaviour: PostgreSQL and scheduler are optional for the core local UI, with local receipt fallback.
- OpenRouter AI routing for approved AI tasks: `openrouter/free` first for low/routine reasoning, a modest paid model for medium reasoning, and a full expensive model for high/deep reasoning. The default modest/full model IDs are configurable with `OPENROUTER_MODEL_MODEST` and `OPENROUTER_MODEL_EXPENSIVE`. Any live call requires `OPENROUTER_API_KEY` and `execute=true`; modest/full paid tiers also require `allow_paid_provider=true`. Without the required key/approval, the app returns a local fallback and records no provider call.
- AMTL calm operating layout: top header, grouped left menu, middle work area, dynamic right context rail, and Admin/Proof separated from normal use.
- Knowledge -> RAG / Sources: internal sources use the approved local NAS source index; internal paths and external references can also be staged as local RAG drafts; pasted source text/excerpts become searchable locally. External URLs can be fetched into local RAG only when the user explicitly approves that one URL fetch; no model/provider call, external send, source-system write, deploy, push, or publish happens from RAG.
- Life Coach / Life Manager v2 local/internal shell: grouped/collapsible left menu, no middle-column scroll, tabbed middle panels, contextual collapsed right rail, state-aware Home, Start My Day, Check In, End My Day, Ask Guide, I Feel Stuck, Decision Help, Deep Inquiry, Voice Notes, Life Map, Promises, Projects, Calendar, Academy, Ask My Sources, RAG / Sources, PIN Strategist, Insights, reviews, privacy, and memory controls.
- PIN Strategist under `Knowledge -> PIN Strategist`: a local Personal Intelligence Network that manages people, sources, questions, influence radar, learning queue, and decision briefs before the user decides what to read, ask, compare, or ignore.
- Local v2 workflow receipts for Life Manager buttons. These prove local button truth without performing external sends, calendar writes, source writes, paid provider calls, or cross-device memory sync.
- CK-owned n8n workflow pack for the four approval-gated automation lanes: OpenRouter paid execution, voice transcription, external calendar writes, and cross-device memory sync. The workflow JSON files are importable and disabled by default; CK exposes local dry-run/preflight endpoints and receipts before any live n8n import or execution.
- Academy screen/module under `Knowledge -> Academy`, with local CK programmes, lessons, practice receipts, and readiness checks. It is a real app module, not just a concept note.
- Live-action gates for voice transcription, Ripple calendar writes, memory sync, and n8n live import/execution. They perform live work only with explicit approval plus configured endpoint/target/key; otherwise they save exact blocked receipts.

## API

### Health

```bash
GET /health
GET /api/health
```

### Practices

```bash
GET /api/practices
GET /api/practices/{practice}
POST /api/practices/{practice}/record
```

### Reflection Prompts

```bash
GET /api/prompts/settings
GET /api/prompts/after-save/{practice}
POST /api/prompts/disable
```

### Difficult Month Mode

```bash
GET /api/difficult-month-mode
POST /api/difficult-month-mode/activate
```

### Local/Internal Proof

```bash
GET /api/product-bible-matrix
GET /api/r2d2
GET /api/ui-truth
GET /api/data-truth
GET /api/dependency-status
GET /api/contextual-guide/{practice}
GET /api/ideas
GET /api/receipts
GET /api/journal/status
GET /api/journal
POST /api/journal
GET /api/journal/{journal_id}
GET /api/inner-work/modes
GET /api/inner-work/sessions
POST /api/inner-work/session
GET /api/inner-work/session/{session_id}
GET /api/guided-use
GET /api/ideas/{idea_id}
GET /api/reports/local-summary
GET /api/reports/local-summary.md
GET /api/synthetic-data/status
GET /api/synthetic-data/removal-preview
POST /api/synthetic-data/cleanup
GET /api/handoffs
POST /api/handoffs/{handover_id}/stage
GET /api/field-utilities
GET /api/cost-effort-reduction
GET /api/oss-adoption
GET /api/ai/model-policy
POST /api/ai/route
POST /api/ai/complete
GET /api/rag/status
POST /api/rag/source-draft
GET /api/rag/source-drafts
GET /api/rag/search
GET /api/pin/status
POST /api/pin/decision-brief
GET /api/pin/people
POST /api/pin/people
GET /api/pin/sources
POST /api/pin/sources
GET /api/pin/questions
POST /api/pin/questions
GET /api/pin/influence-radar
GET /api/pin/learning-queue
GET /api/pin/monthly-review
GET /api/pin/receipts
GET /api/source-index/status
POST /api/source-index/build
GET /api/source-index/search
GET /api/life-manager/spec
GET /api/life-manager/workflows
POST /api/life-manager/receipt
GET /api/life-manager/receipts
GET /api/life-manager/n8n-workflows
GET /api/life-manager/n8n-workflows/{workflow_id}
POST /api/life-manager/n8n-workflows/{workflow_id}/dry-run
POST /api/life-manager/n8n-workflows/{workflow_id}/preflight
GET /api/life-manager/n8n-workflows/receipts
```

## Tech Stack

| Component | Technology |
| --- | --- |
| Backend | FastAPI |
| Frontend | Static calm AMTL Midnight UI |
| Receipts | Local JSONL file outside the repo by default |
| Life Manager v2 Receipts | Local JSONL workflow receipts outside the repo by default |
| n8n Workflow Pack | Disabled importable n8n JSON workflows plus CK local preflight receipts |
| Encrypted Journal | Local encrypted JSONL with Fernet and runtime key file or `CK_LIFE_OS_JOURNAL_KEY` |
| Database | Optional PostgreSQL 5433 adapter |
| Scheduler | Optional APScheduler upgrade path |

## Run Locally

```bash
python main.py
```

The app listens on:

```text
http://127.0.0.1:5420/
```

Smoke check:

```bash
python main.py smoke
```

Tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest beast_test.py -q
```

On Windows PowerShell:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest beast_test.py -q
```

## Standards

- **Language:** Australian English for user-facing copy.
- **Theme:** AMTL Midnight, `#0A0E14` background and `#C9944A` gold accent.
- **Accessibility:** Calm, readable, no pressure mechanics, no fake clickable elements.
- **External actions:** No provider call, external send, source write, deploy, push, or publish is required for local/internal core use.
- **Public/channel truth:** CK Life OS is a local/internal personal practice OS. The Product Bible excludes public publishing, YouTube/social/channel discovery, paid discovery, ad claims, and external customer/source writes from this local/internal completion claim.
- **RAG/Postgres/pgvector truth:** CK Life OS includes a local RAG / Sources surface for approved internal NAS source search, local source drafts, pasted source-text retrieval, and explicit approved one-time external URL fetch into local RAG. PostgreSQL and pgvector remain optional future adapters, not core runtime dependencies.
- **Life Manager v2 truth:** The local/internal v2 shell and button workflows are implemented with local receipts. Live voice transcription, external calendar writes, paid AI execution, cross-device memory sync, and external automations are approval-gated and not claimed as performed.
- **n8n/workflow/live-action truth:** CK includes disabled importable n8n workflows in `n8n/workflows` for paid model execution, voice transcription, calendar writes, and memory sync. Dry-run/preflight proof is local. CK also exposes callable approval gates: `/api/voice/transcription`, `/api/ripple-calendar/write`, `/api/memory/sync`, `/api/life-manager/n8n-workflows/{workflow_id}/live-import`, and `/api/life-manager/n8n-workflows/{workflow_id}/live-execute`. Live work still needs exact approval, credentials/endpoints/targets, and rollback acceptance; missing requirements create blocked local receipts instead of fake success.

## Current Evidence

The C1 local/internal closure evidence is recorded in:

```text
C:\Users\Mani\AMTL-docs\AMTL-AGENT-CONTROL-CENTER\evidence\ck-life-os-local-internal-270626
```

Full reopened Mani 100 local/internal proof uses these Product Bible artifacts:

```text
C:\AMTL\repos\ck-life-os\CK-LIFE-OS-PRODUCT-BIBLE-DELIVERY-MATRIX-270626.md
C:\AMTL\repos\ck-life-os\CK-LIFE-OS-SEMANTIC-PRODUCT-INTENT-ACCEPTANCE-MAP-270626.md
```

The final route, browser, audit-loop, port-truth, and endpoint evidence receipts are written to the same AMTL Agent Control Center evidence folder.

**CK Life OS v1.0** - Almost Magic Tech Lab.
