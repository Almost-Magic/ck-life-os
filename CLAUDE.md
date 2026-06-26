# CLAUDE.md - CK Life OS

## Project

- **Name:** CK Life OS
- **Port:** 5420
- **Status:** DONE_LOCAL_INTERNAL_REGISTERED_OPENROUTER_ROUTING_ENCRYPTED_JOURNAL for the approved local/internal scope
- **Tests:** 47/47 Beast tests passing
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
- `/api/product-bible-matrix`, `/api/r2d2`, `/api/ui-truth`, `/api/data-truth`, and `/api/dependency-status` expose audit truth.
- `/api/ideas` returns 500 local synthetic seed ideas and labels them as synthetic.
- `/api/journal/status`, `/api/journal`, and `/api/journal/{journal_id}` expose the encrypted local journal surface.

## Boundaries

No deploy, publish, external send, source write, paid provider call, or production/customer claim is approved by this file. GitHub push requires Mani's explicit request.
