# CLAUDE.md - CK Life OS

## Project

- **Name:** CK Life OS
- **Port:** 5420
- **Status:** DONE_LOCAL_INTERNAL_REGISTERED_OPENROUTER_ROUTING_ENCRYPTED_JOURNAL_INNER_WORK_RAG_SOURCES_CALM_TABBED_LAYOUT_ACADEMY_PIN_CROSS_APP_PACKETS for the approved local/internal scope
- **Tests:** 65/65 Beast tests passing after Cross-App Packets
- **Front door:** `http://127.0.0.1:5420/`, `http://amtl/ck-life-os/`, and `http://amtl/lifeos/`

## Product Contract

Presence, Reflection, Intention, Gratitude, and Equanimity are the only valid practices. They must remain universal, secular, and free of philosophical tradition labels in the UI.

## Anti-Gamification

- No streaks.
- No scores.
- No badges.
- No comparison view.
- No pressure mechanics.

## Reflection Prompts

- Offered after save, not pushed.
- Optional, never mandatory.
- User can disable prompts completely.

## Local/Internal Truth

- Core UI runs without PostgreSQL, scheduler, provider calls, or unrelated AMTL apps.
- Receipts are written to a local JSONL runtime path outside the repo by default.
- Private journal entries are written to a separate local encrypted JSONL runtime path with Fernet encryption at rest.
- Inner Work sessions are written to encrypted local storage and guide reflection without diagnosis, therapy claims, or spiritual authority claims.
- `/api/product-bible-matrix`, `/api/r2d2`, `/api/ui-truth`, `/api/data-truth`, and `/api/dependency-status` expose audit truth.
- `/api/ideas` returns 500 generated local field/navigation innovation patterns and labels them as generated/synthetic, not lived history.
- `/api/journal/status`, `/api/journal`, and `/api/journal/{journal_id}` expose the encrypted local journal surface.
- `/api/inner-work/modes`, `/api/inner-work/session`, and `/api/inner-work/sessions` expose the encrypted Inner Work surface.
- `/api/ai/model-policy`, `/api/ai/route`, and `/api/ai/complete` route approved AI work through OpenRouter: `openrouter/free` first, modest paid model for medium reasoning, full expensive model for high/deep reasoning. Live calls require `OPENROUTER_API_KEY` plus `execute=true`; modest/full paid tiers also require `allow_paid_provider=true`.
- `Knowledge -> RAG / Sources` exposes `/api/rag/status`, `/api/rag/source-draft`, `/api/rag/source-drafts`, and `/api/rag/search`; internal sources use the approved NAS index, external URLs are draft-only by default, pasted text becomes locally searchable, and explicitly approved one-time URL fetches store fetched text locally without provider/model calls.
- `Knowledge -> Academy` exposes `/api/academy/status`, `/api/academy/programs`, `/api/academy/lessons/{lesson_id}`, `/api/academy/lessons/{lesson_id}/practice`, and `/api/academy/readiness`; it is local-only and writes Academy practice receipts without an external LMS.
- `Knowledge -> PIN Strategist` exposes `/api/pin/status`, `/api/pin/decision-brief`, `/api/pin/people`, `/api/pin/sources`, `/api/pin/questions`, `/api/pin/influence-radar`, `/api/pin/learning-queue`, `/api/pin/monthly-review`, and `/api/pin/receipts`; it is local-only and chooses thinking inputs before decisions. RAG answers/searches sources, while PIN decides what people/sources/questions should feed a decision.
- `Admin / Proof -> Cross-App Packets` exposes `/api/cross-app/notification-rules`, `/api/cross-app/packet-preview`, and `/api/cross-app/packets`; it is packet-first, local-only, and records what CK may tell Elaine, Baldrick, Costanza, Ripple, Spark, Beast, Digital Sentinel, Workshop, Peterman, CK Writer, Creative Studio/Raw Milk, or Opportunity Hunter without silently writing to any target app.
- Live action gates exist for voice transcription, Ripple calendar writes, memory sync, and n8n live import/execution: `/api/voice/transcription`, `/api/ripple-calendar/write`, `/api/memory/sync`, `/api/life-manager/n8n-workflows/{workflow_id}/live-import`, `/api/life-manager/n8n-workflows/{workflow_id}/live-execute`, `/api/live-actions/status`, and `/api/live-actions/receipts`. They perform live work only when explicit approval, approval reference, configured endpoint/target/key, and rollback context are present; otherwise they save exact local blocker receipts.

## Boundaries

No deploy, publish, external send, source write, paid provider call, or production/customer claim is approved by this file. GitHub push requires Mani's explicit request.
