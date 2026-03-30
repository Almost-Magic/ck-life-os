# CK Life OS v1.0

**Five Practices for Living — No Gamification, No Pressure, No Comparison**

- **Port:** 5420
- **Status:** ✅ P7 Complete
- **Tests:** All passing
- **Practices:** 5 universal (Presence, Reflection, Intention, Gratitude, Equanimity)
- **Gamification:** DISABLED (structural)
- **Difficult Month Mode:** First-class feature

## Five Practices

CK Life OS centers on five universal practices that support wellbeing and resilience:

1. **Presence** — Awareness, attention, showing up
2. **Reflection** — Contemplation, processing, understanding
3. **Intention** — Direction, values alignment, deliberate choices
4. **Gratitude** — Appreciation, perspective, recognizing good
5. **Equanimity** — Balance, acceptance, steady perspective

No philosophical tradition is named in the UI. These practices are universal—drawn from wisdom across cultures but presented in secular, accessible language.

## Core Philosophy: No Gamification

CK Life OS is intentionally *anti-gamification*:

### ❌ No Streaks
- Streaks create unhealthy pressure and fear of "breaking the chain"
- They prioritize consistency over authenticity
- Missing a day becomes a failure rather than a rest day

### ❌ No Scores
- Quantifying lived experience corrupts genuine practice
- Scores turn reflection into performance
- Numbers create comparison and judgment

### ❌ No Badges
- Achievement symbols encourage performative practice
- They prioritize external validation over internal growth
- Badges shift motivation from intrinsic to extrinsic

**Why?** Because real practice is about *being*, not *doing*. The moment you're chasing metrics, you've lost the practice.

## Reflection Prompts: Offered, Never Pushed

After recording a practice entry, CK Life OS *offers* a reflection prompt:

- **Opt-in**: You choose whether to respond
- **Never pushed**: No notifications, no reminders, no pressure
- **Can be dismissed**: Click away anytime
- **Can be disabled completely**: Toggle all prompts off in settings

Prompts are suggestions, not requirements. Genuine reflection can't be forced.

## Difficult Month Mode (First-Class Feature)

Life gets hard. CK Life OS has a dedicated mode for when you're struggling:

### What Changes
- **Reflection frequency**: Optional (no pressure to daily practice)
- **Prompt tone**: More compassionate, gentler language
- **Goal tracking**: Disabled (no additional pressure)
- **Comparison view**: Hidden (don't compare to "normal" patterns)

### How to Use
Simply activate Difficult Month Mode in settings. Everything adjusts immediately. Exit anytime—there's no judgment.

This isn't a hidden "sad mode"—it's a first-class feature because difficult months are part of life.

## API

### Practices
```bash
GET /api/practices
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

## Design Philosophy

> *"Your practice should amplify your genuine reflection, not manufacture your attention."*

CK Life OS is built on **trust and introspection**, not engagement metrics:

- No streaks = freedom to rest without guilt
- No scores = focus on being, not doing
- No badges = practice for its own sake
- Difficult Month Mode = compassion when you're struggling
- Optional prompts = reflection that respects your autonomy

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI |
| Database | PostgreSQL 5433 |
| Frontend | AMTL Midnight theme |
| Scheduler | APScheduler (for daily practice reminders, opt-in) |

## Deployment

```bash
python main.py
# Listens on http://localhost:5420

# Requires
- PostgreSQL 5433 (ck_life_os database)
- AMTL Midnight theme (#0A0E14, #C9944A)
```

## Standards

- **Port:** 5420
- **Database:** PostgreSQL `ck_life_os`
- **Language:** Australian English
- **Theme:** AMTL Midnight
- **Accessibility:** WCAG AA

---

**CK Life OS v1.0** — Almost Magic Tech Lab — March 2026
*"Five Practices for Living. No Metrics. No Pressure. Just Practice."*
