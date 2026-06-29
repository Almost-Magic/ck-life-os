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
5. Open `Inner work` when you want guided shadow integration, observation/inquiry, grounding, or relationship-pattern reflection.
6. Use `Optional prompt` only if reflection feels useful.
7. Use `Explain gently` for the ELI10 helper.
8. Use `Make today gentler` to activate Difficult Month Mode.

Leaving the note blank is allowed. Missing a day is allowed. There are no streaks, scores, badges, or comparison mechanics.

## Layout

The app uses the AMTL operating layout:

- Top header with AMTL logo, CK Life OS logo/name, today's local signal, date/time/status, and AMTL seal.
- Left grouped menu with normal practice work first and Admin / Proof collapsed separately.
- Middle work area for practice, encrypted journal, Inner work, guide, Academy, PIN Strategist, Innovation lens, RAG / Sources, Cross-App Packets, reports, and proof summaries.
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

## RAG / Sources

Open `Knowledge`, then `RAG / Sources`.

- Use `RAG status` to see where RAG lives, which internal roots are indexed, and the exact two excluded folders.
- Use `Add source` to stage an internal path or an external URL/reference.
- External URLs are draft-only by default. Tick the one-time approval box only when you want that exact URL fetched into local RAG.
- Paste source text or an excerpt when you already have it and want it searchable locally without a fetch.
- Use `Search` to search the approved local/NAS source index, local RAG drafts with pasted text, and any approved-fetched URL text.
- Use `Results` to inspect matches. Search does not call OpenRouter, pgvector, or an external provider.

Use `Knowledge -> Ask My Sources` when you want an answer from sources. Use `Knowledge -> RAG / Sources` when you want to add, inspect, index, or search source material. Use `Knowledge -> PIN Strategist` when you want to decide which people, sources, questions, and perspectives should feed your thinking before a decision.

## PIN Strategist

Open `Knowledge`, then `PIN Strategist`.

PIN means Personal Intelligence Network. It manages people, books, sources, mentors, ideas, questions, signals, and patterns that feed thinking.

- Use `Before Deciding` to build an input map for a decision or question.
- Use `People` to see mentors, trusted voices, counter-voices, and over-influence notes.
- Use `Sources` to see source trust/use boundaries and jump to RAG / Sources when a source should become searchable.
- Use `Influence Radar` to check over-used people, ideas, or sources.
- Use `Questions` for question-bank prompts before deciding.
- Use `Learning Queue` to choose read, ask, compare, revisit, ignore, or too-much-now lanes.
- Use `PIN Review` to generate a local review of what shaped your thinking.

PIN is local-only by default. It does not call a provider, send externally, or fetch sources silently.

## Cross-App Packets

Open `Admin / Proof`, then `Cross-App Packets`.

This is where CK prepares safe local review packets for other AMTL apps. It answers who should be informed, when, how, why, and what must stay private.

- Use `Rules` to see receiver rules for Elaine, Baldrick, Costanza, Ripple, Spark, Beast, Digital Sentinel, Workshop, Peterman, CK Writer, Creative Studio / Raw Milk, and Opportunity Hunter.
- Use `Automation` to see event-to-receiver rules and run the local automation proof.
- Use `Run 3 automation tests` to create three automated local packet runs and linked packet receipts without sending anything.
- Use `Draft Packet` to choose a receiver and create a sanitised packet preview.
- Use `Save local packet` to save a local receipt only.
- Use `Receipts` to confirm what was prepared and that no sibling app was touched.
- Use `Boundaries` to review the no-silent-write and no-raw-private-material rule.

Cross-App automation creates local packet receipts only. It does not send to another app, call a provider, write a source system, or expose raw journal/shadow/voice/private relationship material. A future receiver adapter would still need exact approval.

## Academy

Open `Knowledge`, then `Academy`.

- Use `Refresh Academy` to load local CK programmes.
- Use `Open lessons` to see lessons that name the matching CK screen path and buttons.
- Use `Start lesson` to jump to the real screen when a lesson has a matching workflow.
- Use `Save practice receipt` to record a local learning note.
- Use `Check readiness` to see local lesson coverage.

Academy does not write to an external LMS and does not call a provider.

## Live Action Gates

Voice transcription, Ripple calendar writes, memory sync, paid OpenRouter execution, and n8n live import/execution are approval-gated. CK exposes callable gates for them, but live work only happens when the matching endpoint/key/target is configured and the request includes explicit approval plus an approval reference. Without that, CK saves a local blocked receipt that explains the exact missing requirement.

## Data Truth

Practice receipts are local JSONL receipts. The 500 catalogue is now a generated field-level and navigation-level innovation lens: each item carries usefulness, user control, calm disclosure, cost/effort reduction, neurodivergent support, contextual 6W/ELI10, and a small mood-lightener. It is labelled as generated local fixture data, not lived history. OpenRouter is the approved AI provider route for AI work, using `openrouter/free` first for low/routine reasoning, a modest paid model for medium reasoning, and a full expensive model for high/deep reasoning. No live provider call happens unless a server-side `OPENROUTER_API_KEY` exists and the request explicitly sets `execute=true`; modest/full paid tiers also require `allow_paid_provider=true`.

Encrypted journal entries are stored in a separate local encrypted JSONL file. Title and content are encrypted at rest with Fernet using either `CK_LIFE_OS_JOURNAL_KEY` or a local runtime key file. The local UI can decrypt entries for review; no external send or source write happens.

Inner Work sessions are also encrypted at rest. They accept text or a pasted voice transcript and return a guide posture, one first question, and a slow program. They are not therapy, diagnosis, or spiritual authority, and the safety brake switches to grounding if the input suggests immediate risk.

No external send, external source write, external LMS write, or paid provider call is required for local/internal use.

RAG / Sources is local-first. PostgreSQL-backed semantic search and pgvector remain optional future infrastructure only; the current local/internal app uses local source drafts, pasted/approved-fetched source text, and the approved NAS source index.
