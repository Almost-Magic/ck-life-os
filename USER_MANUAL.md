# CK Life OS User Manual

Author: Mani Padisetti

## Open The App

Local direct route:

```text
http://127.0.0.1:5420/
```

AMTL gateway routes:

```text
http://amtl/ck-life-os/
http://amtl/lifeos/
```

## Use The Practice Surface

1. Choose one of the five practices.
2. Add a short note if useful.
3. Select `Record`.
4. Open `Encrypted journal` when you want a fuller private reflection encrypted at rest.
5. Use `Optional prompt` only if reflection feels useful.
6. Use `Explain gently` for the ELI10 helper.
7. Use `Make today gentler` to activate Difficult Month Mode.

Leaving the note blank is allowed. Missing a day is allowed. There are no streaks, scores, badges, or comparison mechanics.

## Layout

The app uses the AMTL operating layout:

- Top header with AMTL logo, CK Life OS logo/name, today's local signal, date/time/status, and AMTL seal.
- Left grouped menu with normal practice work first and Admin / Proof collapsed separately.
- Middle work area for practice, encrypted journal, guide, Innovation lens, reports, and proof summaries.
- Right context rail showing next action, selected detail, receipt/evidence, and contextual What / Who / Why / When / How / Where / ELI10.

## Admin / Proof

Open `Admin / Proof`, then `Evidence summaries`. These buttons read live backend routes:

- Product Bible matrix.
- R2D2 equivalent.
- Dependency-down behaviour.
- Data truth.
- Button and drilldown truth.
- OpenRouter model routing.
- Receipt ledger.

These panels are there so the app does not make invisible claims.

## Data Truth

Practice receipts are local JSONL receipts. The 500 catalogue is now a generated field-level and navigation-level innovation lens: each item carries usefulness, user control, calm disclosure, cost/effort reduction, neurodivergent support, contextual 6W/ELI10, and a small mood-lightener. It is labelled as generated local fixture data, not lived history. OpenRouter is the approved AI provider route for AI work, using free, modest-cost, and full-cost model tiers by reasoning level. No live provider call happens unless a server-side `OPENROUTER_API_KEY` exists and the request explicitly sets `execute=true` and `allow_paid_provider=true`.

Encrypted journal entries are stored in a separate local encrypted JSONL file. Title and content are encrypted at rest with Fernet using either `CK_LIFE_OS_JOURNAL_KEY` or a local runtime key file. The local UI can decrypt entries for review; no external send or source write happens.

No external send, source write, or paid provider call is required for local/internal use.

RAG, pgvector, uploaded-file retrieval, and PostgreSQL-backed semantic search are not required for the approved local/internal CK Life OS scope. PostgreSQL remains optional future infrastructure only.
