# CK Life OS v1.0

**Five Practices for Living - No Gamification, No Pressure, No Comparison**

- **Port:** 5420
- **Status:** DONE_LOCAL_INTERNAL_REGISTERED_OPENROUTER_ROUTING_ENCRYPTED_JOURNAL for the approved local/internal scope
- **Tests:** Beast/FastAPI tests, smoke, route, gateway, browser QA, matrix, and semantic map proof
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
- 6W and ELI10 contextual guide drilldowns for every practice.
- Field-level helper text for each practice card.
- A 500-item local field/navigation innovation catalogue absorbed through the Innovation lens, not exposed as a raw register.
- Product Bible matrix, R2D2-equivalent, UI truth, data truth, dependency-status, and receipt proof endpoints.
- Guided-use, report/export, synthetic-data hygiene, OSS adoption truth, cost/effort-reduction truth, local handoff gate, delivery matrix, and semantic intent map artifacts.
- Dependency-down behaviour: PostgreSQL and scheduler are optional for the core local UI, with local receipt fallback.
- OpenRouter AI routing for approved AI tasks: free-tier preference for low reasoning, modest-cost tier for medium reasoning, expensive/full tier for high reasoning. Live calls require `OPENROUTER_API_KEY`, `execute=true`, and `allow_paid_provider=true`; otherwise the app returns a local fallback and records no provider call.
- AMTL calm operating layout: top header, grouped left menu, middle work area, dynamic right context rail, and Admin/Proof separated from normal use.

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
```

## Tech Stack

| Component | Technology |
| --- | --- |
| Backend | FastAPI |
| Frontend | Static calm AMTL Midnight UI |
| Receipts | Local JSONL file outside the repo by default |
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
- **RAG/Postgres/pgvector truth:** CK Life OS does not need uploaded files, private document retrieval, semantic search, or customer/source knowledge for its approved local/internal scope. RAG and pgvector are therefore explicitly out of scope for this product slice; PostgreSQL remains an optional future adapter, not a core runtime dependency.

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
