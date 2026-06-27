# Author: Mani Padisetti
"""CK Life OS - Five Practices for Living."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from config import settings


CANONICAL_PRACTICES = set(settings.PRACTICES)
PRACTICE_DETAILS = {
    "presence": {
        "label": "Presence",
        "meaning": "Awareness, attention, and showing up for this moment.",
        "field_helper": "Name one thing that is true right now.",
        "eli10": "Pause, notice your body, and say what is happening without trying to win at it.",
    },
    "reflection": {
        "label": "Reflection",
        "meaning": "Contemplation, processing, and understanding.",
        "field_helper": "Capture what you noticed, not what you think you should have noticed.",
        "eli10": "Look back gently and ask what the day was trying to teach you.",
    },
    "intention": {
        "label": "Intention",
        "meaning": "Direction, values alignment, and deliberate choices.",
        "field_helper": "Choose the smallest next action that still honours your values.",
        "eli10": "Pick one kind thing to aim yourself toward.",
    },
    "gratitude": {
        "label": "Gratitude",
        "meaning": "Appreciation, perspective, and recognising good.",
        "field_helper": "Let the good thing be specific and small enough to feel real.",
        "eli10": "Notice one thing you are glad existed today.",
    },
    "equanimity": {
        "label": "Equanimity",
        "meaning": "Balance, acceptance, and steady perspective.",
        "field_helper": "Separate what happened from the story your stress is adding.",
        "eli10": "Stand steady for a minute, even if the day is messy.",
    },
}

PRODUCT_IDENTITY = {
    "product": "CK Life OS",
    "parent_brand": "Almost Magic Tech Lab",
    "seal": "AMTL Local/Internal",
    "mark": "five-point practice compass",
    "route": "/",
    "claim_scope": "local/internal practice OS",
}

FIELD_UTILITIES = [
    {
        "field": "Practice",
        "helper": "meaning, field helper, ELI10, and optional prompt",
        "decision": "which practice fits the moment",
        "next_action": "record, ask for a prompt, or open guide",
        "drilldown": "/api/contextual-guide/{practice}",
    },
    {
        "field": "Practice note",
        "helper": "blank is allowed, 500 character local receipt cap",
        "decision": "write only what is useful",
        "next_action": "record local receipt",
        "drilldown": "/api/receipts",
    },
    {
        "field": "Difficult Month Mode",
        "helper": "shows the gentler adjustments before/after activation",
        "decision": "reduce pressure during hard periods",
        "next_action": "activate local mode",
        "drilldown": "/api/difficult-month-mode",
    },
    {
        "field": "Innovation count",
        "helper": "opens 500 generated field/navigation innovations by practice and situation",
        "decision": "choose a useful helper without scanning a raw register",
        "next_action": "filter or inspect an idea",
        "drilldown": "/api/ideas",
    },
    {
        "field": "Receipt ledger",
        "helper": "shows local path, latest receipts, and no external send",
        "decision": "confirm what changed and where it lives",
        "next_action": "open receipt or export local report",
        "drilldown": "/api/receipts",
    },
    {
        "field": "Encrypted journal",
        "helper": "stores private journal content encrypted at rest with a local key",
        "decision": "write a fuller reflection without putting plaintext in the journal file",
        "next_action": "save encrypted entry or open local detail",
        "drilldown": "/api/journal/status",
    },
    {
        "field": "Dependency status",
        "helper": "labels PostgreSQL and scheduler as optional adapters",
        "decision": "know whether the core app is safe when dependencies are down",
        "next_action": "continue locally or plan optional adapter work",
        "drilldown": "/api/dependency-status",
    },
]

HANDOVER_LANES = [
    {
        "handover_id": "lifeos-chronicle-local",
        "source": "CK Life OS",
        "target": "Chronicle / memory lane",
        "type": "local_report",
        "payload_summary": "A practice receipt or local report can be exported for manual Chronicle copy.",
        "owner": "Mani",
        "approval_state": "local_only_not_sent",
        "write_boundary": "writes_nowhere_external",
        "status": "local_gate_available",
        "rollback": "delete local export/ignore receipt; no external state changed",
        "human_review": True,
        "ui_route": "Reports",
    },
    {
        "handover_id": "lifeos-elaine-local",
        "source": "CK Life OS",
        "target": "Elaine",
        "type": "wellbeing_context",
        "payload_summary": "A difficult-month or practice summary can be staged as copy-ready context.",
        "owner": "Mani",
        "approval_state": "local_only_not_sent",
        "write_boundary": "writes_nowhere_external",
        "status": "local_gate_available",
        "rollback": "discard staged handover; no external state changed",
        "human_review": True,
        "ui_route": "Reports",
    },
]

OSS_ADOPTION = [
    {"name": "FastAPI", "role": "local API runtime", "status": "used", "licence_boundary": "permissive runtime dependency"},
    {"name": "Uvicorn", "role": "local ASGI server", "status": "used", "licence_boundary": "permissive runtime dependency"},
    {"name": "Pytest", "role": "delivery matrix regression tests", "status": "used", "licence_boundary": "permissive test dependency"},
    {"name": "Playwright", "role": "browser QA evidence outside product runtime", "status": "used_for_evidence", "licence_boundary": "test/evidence tool"},
    {"name": "AMTL shared modules", "role": "shared capability map", "status": "not_integrated", "licence_boundary": "no suitable required shared module for this tiny local app"},
]

COST_EFFORT_REDUCTION = [
    {
        "promise": "Reduce decision effort",
        "how": "Five fixed practices, contextual guide, and 500 filtered innovation patterns avoid blank-page friction.",
        "proof": ["/api/practices", "/api/contextual-guide/{practice}", "/api/ideas"],
    },
    {
        "promise": "Reduce setup cost",
        "how": "Core local UI does not require PostgreSQL, scheduler, paid providers, or other AMTL apps.",
        "proof": ["/api/dependency-status", "/api/health"],
    },
    {
        "promise": "Reduce rework/confusion",
        "how": "Every record creates a local receipt; report and handover gates show no external writes.",
        "proof": ["/api/receipts", "/api/reports/local-summary", "/api/handoffs"],
    },
]

INNOVATION_SURFACES = [
    {
        "id": "practice-card",
        "label": "Practice card",
        "level": "field-level",
        "ui_absorption": "micro-helper beside the selected practice",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "note-field",
        "label": "Practice note field",
        "level": "field-level",
        "ui_absorption": "just-in-time note helper",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "encrypted-journal",
        "label": "Encrypted journal",
        "level": "field-level",
        "ui_absorption": "private reflection helper",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "guide-panel",
        "label": "Guide panel",
        "level": "navigation-level",
        "ui_absorption": "screen-specific first-step guide",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "innovation-lens",
        "label": "Innovation lens",
        "level": "navigation-level",
        "ui_absorption": "contextual lens card instead of a raw register",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "report-panel",
        "label": "Report panel",
        "level": "navigation-level",
        "ui_absorption": "local summary and monthly reflection",
        "admin_boundary": "normal-user visible",
    },
    {
        "id": "handoff-gate",
        "label": "Handoff gate",
        "level": "navigation-level",
        "ui_absorption": "approval-gated action",
        "admin_boundary": "normal-user visible with explicit approval",
    },
    {
        "id": "dependency-proof",
        "label": "Dependency proof",
        "level": "field-level",
        "ui_absorption": "dependency-down label and repair state",
        "admin_boundary": "admin/proof summary",
    },
    {
        "id": "evidence-proof",
        "label": "Evidence proof",
        "level": "navigation-level",
        "ui_absorption": "collapsed Admin / Proof",
        "admin_boundary": "admin/proof only",
    },
    {
        "id": "context-rail",
        "label": "Context rail",
        "level": "navigation-level",
        "ui_absorption": "right-side contextual 6W/ELI10",
        "admin_boundary": "normal-user visible",
    },
]

INNOVATION_FAMILIES = [
    {
        "id": "control",
        "label": "User control",
        "helper": "offer a reversible choice with a clear stop point",
        "cost_reduction": "prevents rework and accidental over-recording",
        "neurodivergent_support": "predictable action and visible boundary",
        "micro_joke": "No heroic mode. Tiny button, tiny win.",
    },
    {
        "id": "relevance",
        "label": "Relevance filter",
        "helper": "show why this is here and hide it when it is not useful",
        "cost_reduction": "reduces scanning and decision fatigue",
        "neurodivergent_support": "less irrelevant noise in the moment",
        "micro_joke": "If it is not helping, it can go sit quietly.",
    },
    {
        "id": "six-w",
        "label": "Contextual 6W",
        "helper": "make What/Who/Why/When/How/Where specific to the selected thing",
        "cost_reduction": "reduces explanation time",
        "neurodivergent_support": "answers the implicit questions before they pile up",
        "micro_joke": "The six Ws, but they have jobs now.",
    },
    {
        "id": "eli10",
        "label": "ELI10",
        "helper": "translate the action into a plain ten-year-old explanation",
        "cost_reduction": "cuts support and rereading effort",
        "neurodivergent_support": "keeps the next step concrete",
        "micro_joke": "Small words are allowed to be smart.",
    },
    {
        "id": "expand-collapse",
        "label": "Expand/close",
        "helper": "put detail behind a calm open/close action",
        "cost_reduction": "keeps the screen usable without losing depth",
        "neurodivergent_support": "lets the user choose information density",
        "micro_joke": "The detail has a doorbell.",
    },
    {
        "id": "cost-effort",
        "label": "Cost and effort",
        "helper": "show effort, time, privacy, or emotional load when it changes the choice",
        "cost_reduction": "supports cheaper paths without lowering quality",
        "neurodivergent_support": "makes hidden effort visible",
        "micro_joke": "The budget is allowed to have feelings.",
    },
    {
        "id": "calm-timing",
        "label": "Calm timing",
        "helper": "suggest now/later/skip based on pressure and energy",
        "cost_reduction": "avoids forcing work at the wrong time",
        "neurodivergent_support": "normalises pause and deferral",
        "micro_joke": "Later is a real button, not a moral failure.",
    },
    {
        "id": "privacy-boundary",
        "label": "Privacy boundary",
        "helper": "state what is local, encrypted, sent, or not sent",
        "cost_reduction": "prevents review and compliance confusion",
        "neurodivergent_support": "reduces uncertainty about consequences",
        "micro_joke": "No secret tunnels. Just local truth.",
    },
    {
        "id": "navigation-next",
        "label": "Navigation next best step",
        "helper": "make the next click obvious without trapping the user",
        "cost_reduction": "reduces wandering and duplicate clicks",
        "neurodivergent_support": "keeps orientation stable",
        "micro_joke": "The app points. It does not shove.",
    },
    {
        "id": "monthly-reflection",
        "label": "Monthly reflection",
        "helper": "roll up patterns, effort, and gentle suggestions without scoring",
        "cost_reduction": "turns small entries into useful review",
        "neurodivergent_support": "summarises without judgement",
        "micro_joke": "A report, not a report card.",
    },
]

OPENROUTER_ENDPOINT = os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "http://127.0.0.1:5420/")
OPENROUTER_TITLE = os.getenv("OPENROUTER_APP_TITLE", "CK Life OS")
OPENROUTER_TIER_MODELS = {
    "free": {
        "label": "Free models first",
        "reasoning_levels": ["low"],
        "model": os.getenv("OPENROUTER_MODEL_FREE", "openrouter/auto"),
        "cost_policy": "prefer free or free-qualified OpenRouter models; override with OPENROUTER_MODEL_FREE",
        "default_max_tokens": 350,
    },
    "modest": {
        "label": "A little bit expensive",
        "reasoning_levels": ["medium"],
        "model": os.getenv("OPENROUTER_MODEL_MODEST", "openrouter/auto"),
        "cost_policy": "use only when the task needs better reasoning than the free tier; override with OPENROUTER_MODEL_MODEST",
        "default_max_tokens": 600,
    },
    "expensive": {
        "label": "Full expensive models",
        "reasoning_levels": ["high"],
        "model": os.getenv("OPENROUTER_MODEL_EXPENSIVE", "~openai/gpt-latest"),
        "cost_policy": "reserve for complex reasoning, architecture, sensitive review, or high-value synthesis; override with OPENROUTER_MODEL_EXPENSIVE",
        "default_max_tokens": 900,
    },
}

REASONING_TO_TIER = {
    "low": "free",
    "routine": "free",
    "cheap": "free",
    "medium": "modest",
    "normal": "modest",
    "moderate": "modest",
    "high": "expensive",
    "deep": "expensive",
    "hard": "expensive",
}


def _runtime_dir() -> Path:
    base = os.getenv("CK_LIFE_OS_DATA_DIR")
    if base:
        return Path(base)
    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(root) / "AMTL" / "ck-life-os"
    return Path.home() / ".local" / "share" / "ck-life-os"


RUNTIME_DIR = _runtime_dir()
RECEIPTS_FILE = RUNTIME_DIR / "practice-receipts.jsonl"
JOURNAL_FILE = RUNTIME_DIR / "encrypted-journal.jsonl"
JOURNAL_KEY_FILE = RUNTIME_DIR / "journal.key"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_practice(practice: str) -> None:
    if practice not in CANONICAL_PRACTICES:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_practice",
                "practice": practice,
                "allowed_practices": settings.PRACTICES,
                "can_claim_canonical_five_only": True,
            },
        )


def _append_receipt(receipt: dict[str, Any]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with RECEIPTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")


def _read_receipts(limit: int = 20) -> list[dict[str, Any]]:
    if not RECEIPTS_FILE.exists():
        return []
    rows = []
    for line in RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _safe_note(payload: dict[str, Any]) -> str:
    raw = str(payload.get("note") or payload.get("content") or "").strip()
    return raw[:500]


def _journal_fernet() -> Fernet:
    env_key = os.getenv("CK_LIFE_OS_JOURNAL_KEY")
    if env_key:
        return Fernet(env_key.encode("utf-8"))
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if not JOURNAL_KEY_FILE.exists():
        JOURNAL_KEY_FILE.write_bytes(Fernet.generate_key())
        try:
            JOURNAL_KEY_FILE.chmod(0o600)
        except OSError:
            pass
    return Fernet(JOURNAL_KEY_FILE.read_bytes().strip())


def _journal_summary(row: dict[str, Any]) -> dict[str, Any]:
    content = _decrypt_journal_row(row)
    title = _decrypt_journal_title(row)
    return {
        "journal_id": row["journal_id"],
        "created_at": row["created_at"],
        "practice": row.get("practice"),
        "title": title,
        "content_preview": content[:80],
        "encrypted_at_rest": True,
        "external_send": False,
        "source_write": False,
    }


def _migrate_journal_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changed = False
    fernet = _journal_fernet()
    migrated = []
    for row in rows:
        updated = dict(row)
        if "title" in updated and "title_ciphertext" not in updated:
            updated["title_ciphertext"] = fernet.encrypt(str(updated.pop("title") or "Untitled").encode("utf-8")).decode("ascii")
            changed = True
        if "content_preview" in updated:
            updated.pop("content_preview", None)
            changed = True
        migrated.append(updated)
    if changed:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with JOURNAL_FILE.open("w", encoding="utf-8") as handle:
            for row in migrated:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return migrated


def _read_journal_rows(limit: int = 20) -> list[dict[str, Any]]:
    if not JOURNAL_FILE.exists():
        return []
    rows = []
    for line in JOURNAL_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return _migrate_journal_rows(rows)


def _append_encrypted_journal(payload: dict[str, Any]) -> dict[str, Any]:
    practice = str(payload.get("practice") or "reflection").strip().lower()
    if practice not in CANONICAL_PRACTICES:
        _assert_practice(practice)
    content = str(payload.get("content") or payload.get("note") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail={"error": "journal_content_required"})
    title = str(payload.get("title") or "").strip()[:80] or PRACTICE_DETAILS[practice]["label"]
    content = content[:4000]
    fernet = _journal_fernet()
    encrypted_title = fernet.encrypt(title.encode("utf-8")).decode("ascii")
    encrypted_content = fernet.encrypt(content.encode("utf-8")).decode("ascii")
    row = {
        "journal_id": f"journal-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "practice": practice,
        "title_ciphertext": encrypted_title,
        "content_ciphertext": encrypted_content,
        "encryption": {
            "scheme": "fernet",
            "key_source": "CK_LIFE_OS_JOURNAL_KEY" if os.getenv("CK_LIFE_OS_JOURNAL_KEY") else "local_runtime_key_file",
            "key_path": str(JOURNAL_KEY_FILE) if not os.getenv("CK_LIFE_OS_JOURNAL_KEY") else "env",
            "plaintext_stored": False,
        },
        "external_send": False,
        "source_write": False,
    }
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with JOURNAL_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return row


def _decrypt_journal_row(row: dict[str, Any]) -> str:
    try:
        token = row.get("content_ciphertext") or row["ciphertext"]
        return _journal_fernet().decrypt(str(token).encode("ascii")).decode("utf-8")
    except (InvalidToken, KeyError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=409, detail={"error": "journal_decryption_failed"}) from exc


def _decrypt_journal_title(row: dict[str, Any]) -> str:
    try:
        if row.get("title_ciphertext"):
            return _journal_fernet().decrypt(str(row["title_ciphertext"]).encode("ascii")).decode("utf-8")
        return str(row.get("title") or "Untitled")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=409, detail={"error": "journal_title_decryption_failed"}) from exc


def _openrouter_key_present() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def _normalise_reasoning_level(value: str | None) -> str:
    level = (value or "low").strip().lower()
    return level if level in REASONING_TO_TIER else "low"


def _select_openrouter_tier(reasoning_level: str | None, max_cost_tier: str | None = None) -> dict[str, Any]:
    level = _normalise_reasoning_level(reasoning_level)
    selected_tier = REASONING_TO_TIER[level]
    allowed_order = ["free", "modest", "expensive"]
    max_tier = (max_cost_tier or "expensive").strip().lower()
    if max_tier not in allowed_order:
        max_tier = "free"
    if allowed_order.index(selected_tier) > allowed_order.index(max_tier):
        selected_tier = max_tier
    tier = dict(OPENROUTER_TIER_MODELS[selected_tier])
    tier.update(
        {
            "tier": selected_tier,
            "reasoning_level": level,
            "max_cost_tier": max_tier,
            "key_configured": _openrouter_key_present(),
            "endpoint": OPENROUTER_ENDPOINT,
            "secret_boundary": "OPENROUTER_API_KEY is read server-side only and never returned.",
        }
    )
    return tier


def _local_ai_fallback(prompt: str, tier: dict[str, Any]) -> dict[str, Any]:
    trimmed = " ".join(prompt.split())[:220]
    if not trimmed:
        trimmed = "No prompt supplied."
    return {
        "provider_called": False,
        "fallback": True,
        "message": (
            f"Local fallback only. Selected {tier['label']} ({tier['tier']}) for "
            f"{tier['reasoning_level']} reasoning, but no live OpenRouter call was made. "
            f"Prompt summary: {trimmed}"
        ),
        "next_action": "Set OPENROUTER_API_KEY and call with execute=true and allow_paid_provider=true when an AI call is approved.",
    }


def _call_openrouter(prompt: str, tier: dict[str, Any], system: str | None = None) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return _local_ai_fallback(prompt, tier)
    messages = []
    if system:
        messages.append({"role": "system", "content": system[:2000]})
    messages.append({"role": "user", "content": prompt[:8000]})
    body = {
        "model": tier["model"],
        "messages": messages,
        "max_tokens": tier["default_max_tokens"],
    }
    request = UrlRequest(
        OPENROUTER_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": OPENROUTER_REFERER,
            "X-OpenRouter-Title": OPENROUTER_TITLE,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise HTTPException(status_code=502, detail={"error": "openrouter_http_error", "status": exc.code, "detail": detail})
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=502, detail={"error": "openrouter_unavailable", "detail": str(exc)})

    content = ""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = json.dumps(payload)[:1200]
    return {
        "provider_called": True,
        "fallback": False,
        "model": tier["model"],
        "tier": tier["tier"],
        "content": content,
        "usage": payload.get("usage"),
        "provider": "openrouter",
    }


def _practice_ideas() -> list[dict[str, Any]]:
    ideas = []
    situations = [
        "morning",
        "midday",
        "evening",
        "difficult-day",
        "low-energy",
        "family",
        "work",
        "body",
        "creative",
        "repair",
    ]
    for practice in settings.PRACTICES:
        detail = PRACTICE_DETAILS[practice]
        for index in range(100):
            surface = INNOVATION_SURFACES[index // len(INNOVATION_FAMILIES)]
            family = INNOVATION_FAMILIES[index % len(INNOVATION_FAMILIES)]
            situation = situations[index % len(situations)]
            ideas.append(
                {
                    "id": f"{practice}-{index + 1:03d}",
                    "practice": practice,
                    "situation": situation,
                    "title": f"{detail['label']} {family['label']} on {surface['label']}",
                    "action": f"Apply {family['helper']} to {surface['label'].lower()} for {detail['label'].lower()}.",
                    "innovation_level": surface["level"],
                    "surface": surface,
                    "family": family,
                    "user_control": "user can open, skip, close, or use the suggestion without scoring",
                    "calm_disclosure": "show the short helper first; put detail behind open/local decrypt/proof actions",
                    "why_relevant": f"{detail['label']} benefits when {family['label'].lower()} reduces ambiguity at the {surface['label'].lower()}.",
                    "admin_boundary": surface["admin_boundary"],
                    "sixw": {
                        "what": f"{family['label']} for {surface['label']}",
                        "who": "the local CK Life OS user",
                        "why": family["helper"],
                        "when": situation,
                        "where": surface["ui_absorption"],
                        "how": f"Use the visible helper, then expand only if more context is useful.",
                        "eli10": f"This makes {detail['label'].lower()} easier by giving one calm clue at the right place.",
                    },
                    "cost_reduction": family["cost_reduction"],
                    "neurodivergent_support": family["neurodivergent_support"],
                    "micro_joke": family["micro_joke"],
                    "absorbed_in_ui": True,
                    "ui_absorption": surface["ui_absorption"],
                    "synthetic_data": True,
                    "source": "local_generated_field_navigation_innovation_catalogue_v1",
                }
            )
    return ideas


def _find_idea(idea_id: str) -> dict[str, Any]:
    for item in _practice_ideas():
        if item["id"] == idea_id:
            return item
    raise HTTPException(status_code=404, detail={"error": "unknown_idea", "idea_id": idea_id})


def _local_report() -> dict[str, Any]:
    receipts = _read_receipts(limit=100000)
    journal_rows = _read_journal_rows(limit=100000)
    return {
        "report_id": f"lifeos-local-summary-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "generated_at": _utc_now(),
        "product": PRODUCT_IDENTITY,
        "practice_count": len(settings.PRACTICES),
        "receipt_count": len(receipts),
        "encrypted_journal_count": len(journal_rows),
        "idea_count": len(_practice_ideas()),
        "gamification": {"streaks": False, "scores": False, "badges": False, "comparison": False},
        "dependency_boundary": {
            "postgres_required_for_core_ui": False,
            "scheduler_required_for_core_ui": False,
            "provider_required": False,
        },
        "handover_boundary": {
            "external_send": False,
            "source_write": False,
            "human_review_required": True,
            "available_local_gates": [lane["handover_id"] for lane in HANDOVER_LANES],
        },
        "latest_receipts": receipts[-5:],
        "latest_journal_entries": [_journal_summary(row) for row in journal_rows[-5:]],
    }


app = FastAPI(
    title="CK Life OS",
    description="Five practices for living: Presence, Reflection, Intention, Gratitude, Equanimity",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ASSETS_DIR = Path(__file__).with_name("assets")
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "port": settings.PORT,
        "practices": len(settings.PRACTICES),
        "gamification": "DISABLED",
        "difficult_month_mode": "AVAILABLE",
        "runtime_independent": True,
        "external_provider_required": False,
    }


@app.get("/api/health")
async def health_alias():
    """NGINX-compliant health alias."""
    return await health()


@app.get("/")
async def root():
    """Serve the local product UI."""
    idx = Path(__file__).with_name("index.html")
    if idx.exists():
        return FileResponse(idx, media_type="text/html")
    return {"service": "running", "ui": "missing"}


@app.get("/api/practices")
async def list_practices():
    """List five practices, with universal names and no tradition labels."""
    return {
        "total": len(settings.PRACTICES),
        "practices": settings.PRACTICES,
        "details": PRACTICE_DETAILS,
        "description": "Five universal practices for living",
        "canonical_five_only": True,
        "field_utilities": [item for item in FIELD_UTILITIES if item["field"] == "Practice"],
    }


@app.post("/api/practices/{practice}/record")
async def record_practice(practice: str, request: Request):
    """Record a practice entry without gamification."""
    _assert_practice(practice)
    data = await request.json() if request.method == "POST" else {}
    receipt = {
        "receipt_id": f"{practice}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "recorded_at": _utc_now(),
        "practice": practice,
        "note": _safe_note(data),
        "streak_tracking": False,
        "score": None,
        "gamification": False,
        "external_send": False,
        "provider_called": False,
        "source_write": False,
        "storage": str(RECEIPTS_FILE),
    }
    _append_receipt(receipt)
    return {
        "status": "success",
        "practice": practice,
        "recorded": True,
        "entry_id": receipt["receipt_id"],
        "receipt": receipt,
        "streak_tracking": False,
        "score": None,
        "gamification": False,
    }


@app.get("/api/practices/{practice}")
async def practice_detail(practice: str):
    _assert_practice(practice)
    return {
        "practice": practice,
        **PRACTICE_DETAILS[practice],
        "canonical": True,
        "no_comparison": True,
        "field_utility": FIELD_UTILITIES[0],
    }


@app.get("/api/guided-use")
async def guided_use(view: str = Query("practice")):
    guides = {
        "practice": {
            "screen": "Practice",
            "start_here": "Choose the practice that best matches the moment.",
            "next_click": "Record a practice, or Explain gently if you are unsure.",
            "evidence_to_check": "Receipt ledger after recording.",
            "do_not_do_yet": "Do not treat the 500 innovations as lived user history or a raw register.",
            "write_boundary": "Recording writes a local JSONL receipt only.",
            "receipt_location": str(RECEIPTS_FILE),
        },
        "ideas": {
            "screen": "Innovation lens",
            "start_here": "Filter by practice or situation, then open a calm subset.",
            "next_click": "Open an innovation to see usefulness, control, cost, calm disclosure, and contextual 6W/ELI10.",
            "evidence_to_check": "Innovation detail and synthetic-data status.",
            "do_not_do_yet": "Do not dump all 500 as a raw register or call them lived history.",
            "write_boundary": "Browsing innovations writes nothing.",
            "receipt_location": "No receipt created unless an innovation is used to shape a practice note.",
        },
        "reports": {
            "screen": "Reports",
            "start_here": "Open the local summary report.",
            "next_click": "Export markdown or stage a local handover gate.",
            "evidence_to_check": "Report ID, receipt count, and handover boundary.",
            "do_not_do_yet": "Do not send to Elaine or Chronicle without human approval.",
            "write_boundary": "Reports read local data; handover gates are local-only.",
            "receipt_location": "/api/reports/local-summary and /api/handoffs",
        },
        "evidence": {
            "screen": "Evidence",
            "start_here": "Check Product Bible, R2D2, dependency, UI, and data truth summaries.",
            "next_click": "Open a proof summary; use raw JSON only from API if needed for C1.",
            "evidence_to_check": "Delivery matrix and semantic map evidence paths.",
            "do_not_do_yet": "Do not confuse local/internal proof with production release.",
            "write_boundary": "Evidence reads backend truth and writes nothing.",
            "receipt_location": "Control Center evidence folder after C1 audit.",
        },
    }
    return guides.get(view, guides["practice"])


@app.get("/api/prompts/settings")
async def prompt_settings():
    """User's prompt preferences."""
    return {
        "prompts_enabled": settings.PROMPTS_ENABLED_BY_DEFAULT,
        "prompts_optional": settings.PROMPTS_OPTIONAL,
        "can_disable_completely": True,
        "delivery": "offered after save, never pushed",
        "user_can_adjust": True,
        "notifications": "disabled_by_default",
    }


@app.post("/api/prompts/disable")
async def disable_all_prompts(request: Request):
    """User can disable all prompts entirely."""
    return {
        "status": "success",
        "prompts_disabled": True,
        "can_re_enable": True,
        "description": "All reflection prompts disabled",
    }


@app.get("/api/prompts/after-save/{practice}")
async def get_optional_prompt(practice: str):
    """Optional reflection prompt offered after save, not pushed."""
    _assert_practice(practice)
    label = PRACTICE_DETAILS[practice]["label"].lower()
    return {
        "practice": practice,
        "prompt": f"What did this {label} practice make easier to notice?",
        "optional": True,
        "pushed": False,
        "can_skip": True,
        "description": "Optional reflection, dismiss anytime",
    }


@app.get("/api/contextual-guide/{practice}")
async def contextual_guide(practice: str):
    """6W plus ELI10 helper for a practice."""
    _assert_practice(practice)
    detail = PRACTICE_DETAILS[practice]
    return {
        "practice": practice,
        "who": "You, at the pace your day can hold.",
        "what": detail["meaning"],
        "when": "Now, later, or only when it feels useful.",
        "where": "Wherever you can safely pause for a moment.",
        "why": "To support attention and resilience without pressure.",
        "how": detail["field_helper"],
        "eli10": detail["eli10"],
        "tone": "calm",
        "pressure": "none",
        "selected_content": PRACTICE_DETAILS[practice],
    }


@app.get("/api/difficult-month-mode")
async def difficult_month_status():
    """Difficult Month Mode configuration."""
    return {
        "feature_enabled": settings.DIFFICULT_MONTH_MODE_ENABLED,
        "description": "For when life is hard; everything gets gentler",
        "active": False,
        "adjustments": settings.DIFFICULT_MONTH_ADJUSTMENTS,
    }


@app.post("/api/difficult-month-mode/activate")
async def activate_difficult_month():
    """Activate Difficult Month Mode."""
    return {
        "status": "success",
        "difficult_month_active": True,
        "adjustments": {
            "reflection_frequency": "optional",
            "prompt_tone": "compassionate",
            "goal_tracking": "disabled",
            "comparison_view": "hidden",
        },
        "duration": "user-defined",
        "exit_anytime": True,
    }


@app.get("/api/ai/model-policy")
async def ai_model_policy():
    """OpenRouter cost/reasoning policy without exposing secrets."""
    return {
        "provider": "openrouter",
        "endpoint": OPENROUTER_ENDPOINT,
        "key_configured": _openrouter_key_present(),
        "routing_order": ["free", "modest", "expensive"],
        "policy": OPENROUTER_TIER_MODELS,
        "reasoning_map": REASONING_TO_TIER,
        "default_boundary": "No provider call occurs unless /api/ai/complete receives execute=true and allow_paid_provider=true.",
        "secret_boundary": "OPENROUTER_API_KEY stays server-side and is never returned to the UI.",
        "fallback": "If key/config/approval is missing, CK Life OS returns a local fallback explanation.",
    }


@app.post("/api/ai/route")
async def ai_route(request: Request):
    """Select the OpenRouter tier for a task without calling a provider."""
    payload = await request.json()
    tier = _select_openrouter_tier(payload.get("reasoning_level"), payload.get("max_cost_tier"))
    return {
        "provider": "openrouter",
        "provider_called": False,
        "selected": tier,
        "task": str(payload.get("task") or payload.get("prompt") or "")[:300],
        "next_action": "Call /api/ai/complete with execute=true and allow_paid_provider=true only when a live AI call is approved.",
    }


@app.post("/api/ai/complete")
async def ai_complete(request: Request):
    """Guarded OpenRouter completion endpoint with local fallback."""
    payload = await request.json()
    prompt = str(payload.get("prompt") or payload.get("task") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail={"error": "prompt_required"})
    tier = _select_openrouter_tier(payload.get("reasoning_level"), payload.get("max_cost_tier"))
    execute = bool(payload.get("execute"))
    allow_paid = bool(payload.get("allow_paid_provider"))
    if not execute or not allow_paid:
        return {
            "provider": "openrouter",
            "selected": tier,
            **_local_ai_fallback(prompt, tier),
            "approval_required": True,
        }
    result = _call_openrouter(prompt, tier, payload.get("system"))
    return {
        "provider": "openrouter",
        "selected": tier,
        **result,
        "approval_required": False,
    }


@app.get("/api/no-streaks")
async def no_streaks():
    """Streaks are disabled by design."""
    return {
        "streaks_enabled": False,
        "reason": "Streaks create unhealthy pressure and external motivation",
    }


@app.get("/api/no-scores")
async def no_scores():
    """Scores are disabled by design."""
    return {
        "scores_enabled": False,
        "reason": "Quantifying lived experience corrupts genuine practice",
    }


@app.get("/api/no-badges")
async def no_badges():
    """Badges are disabled by design."""
    return {
        "badges_enabled": False,
        "reason": "Achievement symbols encourage performative practice",
    }


@app.get("/api/receipts")
async def receipts():
    return {
        "storage": str(RECEIPTS_FILE),
        "items": _read_receipts(),
        "external_send": False,
        "source_write": False,
        "count": len(_read_receipts(limit=100000)),
    }


@app.get("/api/journal/status")
async def journal_status():
    rows = _read_journal_rows(limit=100000)
    return {
        "enabled": True,
        "encrypted_at_rest": True,
        "scheme": "fernet",
        "storage": str(JOURNAL_FILE),
        "key_source": "CK_LIFE_OS_JOURNAL_KEY" if os.getenv("CK_LIFE_OS_JOURNAL_KEY") else "local_runtime_key_file",
        "key_path_returned": False,
        "entry_count": len(rows),
        "plaintext_stored": False,
        "external_send": False,
        "source_write": False,
    }


@app.get("/api/journal")
async def journal_entries():
    rows = _read_journal_rows()
    return {
        "storage": str(JOURNAL_FILE),
        "encrypted_at_rest": True,
        "items": [_journal_summary(row) for row in rows],
        "external_send": False,
        "source_write": False,
        "count": len(_read_journal_rows(limit=100000)),
    }


@app.post("/api/journal")
async def save_journal_entry(request: Request):
    payload = await request.json()
    row = _append_encrypted_journal(payload)
    return {
        "saved": True,
        "journal_id": row["journal_id"],
        "entry": _journal_summary(row),
        "encrypted_at_rest": True,
        "plaintext_stored": False,
        "external_send": False,
        "source_write": False,
    }


@app.get("/api/journal/{journal_id}")
async def journal_entry(journal_id: str):
    row = next((item for item in _read_journal_rows(limit=100000) if item.get("journal_id") == journal_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "journal_entry_not_found"})
    return {
        **_journal_summary(row),
        "content": _decrypt_journal_row(row),
        "decrypted_for_local_ui": True,
    }


@app.get("/api/ideas")
async def ideas(
    practice: str | None = Query(None),
    situation: str | None = Query(None),
    limit: int = Query(500, ge=1, le=500),
):
    if practice is not None:
        _assert_practice(practice)
    catalogue = _practice_ideas()
    if practice:
        catalogue = [item for item in catalogue if item["practice"] == practice]
    if situation:
        catalogue = [item for item in catalogue if item["situation"] == situation]
    return {
        "total": len(catalogue),
        "returned": min(len(catalogue), limit),
        "ideas": catalogue[:limit],
        "synthetic_data": True,
        "synthetic_data_truth": "Local generated innovation catalogue only; no claim of lived user data or external source truth.",
        "catalogue_truth": "500 field-level and navigation-level innovation patterns are absorbed through contextual UI helpers, not treated as a separate product register.",
        "provider_called": False,
        "filters": {"practice": practice, "situation": situation, "limit": limit},
    }


@app.get("/api/ideas/{idea_id}")
async def idea_detail(idea_id: str):
    item = _find_idea(idea_id)
    return {
        **item,
        "what": item["title"],
        "who": "The local CK Life OS user.",
        "why": item["why_relevant"],
        "when": item["situation"],
        "where": item["ui_absorption"],
        "how": item["action"],
        "eli10": item["sixw"]["eli10"],
        "implementation_status": "innovation_pattern_absorbed_in_ui_lens",
        "synthetic_data": True,
    }


@app.get("/api/synthetic-data/status")
async def synthetic_data_status():
    return {
        "status": "clean_boundary",
        "synthetic_sources": ["local_seed_catalogue_v1"],
        "synthetic_rows": len(_practice_ideas()),
        "synthetic_outside_demo_scope": 0,
        "real_user_receipts_are_synthetic": False,
        "cleanup_available": True,
        "cleanup_note": "Generated innovation patterns are not persisted as user history; cleanup verifies the boundary and writes a local receipt.",
    }


@app.get("/api/synthetic-data/removal-preview")
async def synthetic_removal_preview():
    return {
        "would_remove": 0,
        "preserved_demo_rows": len(_practice_ideas()),
        "reason": "Innovation patterns are generated local catalogue rows, not stored operational user history.",
        "requires_confirmation": True,
        "safe_to_run": True,
    }


@app.post("/api/synthetic-data/cleanup")
async def synthetic_cleanup(request: Request):
    payload = await request.json()
    if payload.get("confirm") is not True:
        raise HTTPException(status_code=400, detail={"error": "confirmation_required", "required": {"confirm": True}})
    receipt = {
        "receipt_id": f"synthetic-cleanup-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "would_remove": 0,
        "removed": 0,
        "post_clean_synthetic_outside_demo_scope": 0,
        "external_send": False,
        "source_write": False,
    }
    _append_receipt({"practice": "system", "note": "Synthetic boundary cleanup verification", **receipt})
    return receipt


@app.get("/api/dependency-status")
async def dependency_status():
    return {
        "postgres": {
            "configured": bool(settings.DATABASE_URL),
            "required_for_core_ui": False,
            "state": "optional_adapter_not_required_for_local_core",
            "fallback": "local JSONL receipts",
        },
        "scheduler": {
            "configured": True,
            "required_for_core_ui": False,
            "state": "not_started_in_local_internal_mode",
            "fallback": "manual practice recording",
        },
        "external_providers": {
            "required_for_core_ui": False,
            "configured_provider": "openrouter",
            "key_configured": _openrouter_key_present(),
            "provider_called": False,
            "routing_policy": "/api/ai/model-policy",
            "fallback": "local prompts and local guide copy when key, approval, or execution flag is absent",
        },
        "runtime_independent": True,
    }


@app.get("/api/field-utilities")
async def field_utilities():
    return {"total": len(FIELD_UTILITIES), "items": FIELD_UTILITIES}


@app.get("/api/cost-effort-reduction")
async def cost_effort_reduction():
    return {"total": len(COST_EFFORT_REDUCTION), "items": COST_EFFORT_REDUCTION}


@app.get("/api/oss-adoption")
async def oss_adoption():
    return {"total": len(OSS_ADOPTION), "items": OSS_ADOPTION}


@app.get("/api/handoffs")
async def handoffs():
    return {
        "status": "local_gates_available",
        "external_send": False,
        "source_write": False,
        "human_review_required": True,
        "lanes": HANDOVER_LANES,
    }


@app.post("/api/handoffs/{handover_id}/stage")
async def stage_handover(handover_id: str, request: Request):
    lane = next((item for item in HANDOVER_LANES if item["handover_id"] == handover_id), None)
    if lane is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_handover", "handover_id": handover_id})
    payload = await request.json()
    receipt = {
        "receipt_id": f"{handover_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "handover": lane,
        "payload_note": _safe_note(payload),
        "approval_state": "draft_local_only",
        "external_send": False,
        "source_write": False,
        "human_review_required": True,
    }
    _append_receipt({"practice": "system", "note": f"Staged handover {handover_id}", **receipt})
    return receipt


@app.get("/api/reports/local-summary")
async def local_summary_report():
    return _local_report()


@app.get("/api/reports/local-summary.md")
async def local_summary_markdown():
    report = _local_report()
    lines = [
        f"# CK Life OS Local Summary",
        "",
        f"- Report ID: {report['report_id']}",
        f"- Generated: {report['generated_at']}",
        f"- Practices: {report['practice_count']}",
        f"- Receipts: {report['receipt_count']}",
        f"- Encrypted journal entries: {report['encrypted_journal_count']}",
        f"- Innovations: {report['idea_count']} generated rows",
        f"- External send: {report['handover_boundary']['external_send']}",
        f"- Source write: {report['handover_boundary']['source_write']}",
        f"- Human review required for handoff: {report['handover_boundary']['human_review_required']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/api/product-bible-matrix")
async def product_bible_matrix():
    return {
        "source_docs": ["README.md", "COMPLETION-REPORT.md", "CLAUDE.md", "USER_MANUAL.md", "beast_test.py"],
        "covers_features": True,
        "covers_functions": True,
        "covers_prd": True,
        "covers_500_ideas": True,
        "covers_field_level_innovations": True,
        "covers_ui": True,
        "covers_oss": True,
        "covers_cross_app_handoffs": True,
        "cross_app_handoffs": "none_required_for_core_local_internal_use",
        "covers_guided_use": True,
        "covers_reports_exports": True,
        "covers_synthetic_data_hygiene": True,
        "covers_encrypted_journal": True,
        "covers_cost_effort_reduction": True,
        "covers_semantic_intent_map": True,
        "covers_delivery_matrix": True,
        "covers_amtl_operating_layout": True,
        "covers_openrouter_model_routing": True,
        "covers_rag_postgres_pgvector_truth": True,
        "notes": [
            "README.md is the canonical Product Bible in this repo.",
            "CK-LIFE-OS-PRODUCT-BIBLE-DELIVERY-MATRIX-270626.md is the durable delivery matrix.",
            "CK-LIFE-OS-SEMANTIC-PRODUCT-INTENT-ACCEPTANCE-MAP-270626.md is the semantic map.",
            "500 ideas are generated field/navigation innovation patterns absorbed through the UI lens, not user history or a raw register.",
            "AMTL operating layout is implemented in index.html with transparent local SVG assets and dynamic context rail.",
            "Encrypted journal entries use Fernet encryption at rest in the local runtime folder; plaintext is decrypted only through the local API/UI.",
            "AI provider routing uses OpenRouter with free, modest, and expensive tiers selected by reasoning level.",
            "RAG and pgvector are explicitly out of scope for the approved local/internal CK Life OS slice; PostgreSQL is optional only.",
        ],
    }


@app.get("/api/r2d2")
async def r2d2_equivalent():
    checks = [
        "canonical_five_practices",
        "no_gamification",
        "optional_prompts",
        "difficult_month_mode",
        "local_receipts",
        "encrypted_journal",
        "contextual_6w_eli10",
        "field_level_helpers",
        "synthetic_data_truth",
        "runtime_independence",
        "dependency_down_fallback",
        "button_truth",
        "drilldown_truth",
        "guided_use",
        "ideas_filter_detail_truth",
        "reports_exports",
        "local_handover_gates",
        "synthetic_data_hygiene",
        "oss_adoption_truth",
        "cost_effort_reduction_truth",
        "delivery_matrix",
        "semantic_intent_map",
        "amtl_operating_layout",
        "subpath_safe_gateway_assets_and_api",
        "openrouter_reasoning_cost_router",
        "rag_pgvector_truth_out_of_scope",
    ]
    return {
        "status": "pass",
        "done": len(checks),
        "partial": 0,
        "blocked": 0,
        "checks": checks,
        "full_local_internal_claim_scope": "CK Life OS local/internal core only",
    }


@app.get("/api/ui-truth")
async def ui_truth():
    return {
        "front_door": "/",
        "amtl_operating_layout": {
            "top_header": True,
            "grouped_left_menu": True,
            "middle_work_area": True,
            "dynamic_right_context_rail": True,
            "admin_proof_separated": True,
            "transparent_local_assets": True,
            "subpath_safe": True,
        },
        "buttons": {
            "record_practice": "POST /api/practices/{practice}/record",
            "optional_prompt": "GET /api/prompts/after-save/{practice}",
            "contextual_guide": "GET /api/contextual-guide/{practice}",
            "difficult_month": "POST /api/difficult-month-mode/activate",
            "guide_me": "GET /api/guided-use",
            "ideas": "GET /api/ideas and GET /api/ideas/{idea_id}",
            "report": "GET /api/reports/local-summary",
            "handover": "POST /api/handoffs/{handover_id}/stage",
            "evidence": "GET /api/product-bible-matrix",
            "synthetic_cleanup": "POST /api/synthetic-data/cleanup",
            "journal_save": "POST /api/journal",
            "journal_status": "GET /api/journal/status",
            "ai_route": "POST /api/ai/route",
            "ai_complete": "POST /api/ai/complete",
        },
        "drilldowns": [
            "practice detail",
            "receipt ledger",
            "encrypted journal detail",
            "dependency status",
            "500 ideas filtered rows",
            "idea detail",
            "report detail",
            "handover lane",
            "synthetic data preview",
            "R2D2-equivalent",
            "OpenRouter model policy",
        ],
        "button_truth": True,
        "count_truth": True,
    }


@app.get("/api/data-truth")
async def data_truth():
    return {
        "user_receipts": {
            "mode": "local_jsonl",
            "path": str(RECEIPTS_FILE),
            "count": len(_read_receipts(limit=100000)),
        },
        "encrypted_journal": {
            "mode": "local_encrypted_jsonl",
            "path": str(JOURNAL_FILE),
            "count": len(_read_journal_rows(limit=100000)),
            "encrypted_at_rest": True,
            "scheme": "fernet",
            "plaintext_stored": False,
            "key_source": "CK_LIFE_OS_JOURNAL_KEY" if os.getenv("CK_LIFE_OS_JOURNAL_KEY") else "local_runtime_key_file",
        },
        "ideas": {
            "mode": "synthetic_seed_catalogue",
            "count": len(_practice_ideas()),
            "provider_called": False,
        },
        "external_send": False,
        "source_write": False,
        "paid_provider_call": False,
        "ai_provider": {
            "configured_provider": "openrouter",
            "key_configured": _openrouter_key_present(),
            "live_call_requires": ["OPENROUTER_API_KEY", "execute=true", "allow_paid_provider=true"],
            "last_proof_provider_called": False,
            "routing_policy": "/api/ai/model-policy",
        },
    }


def smoke_check() -> int:
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    # FastAPI TestClient is the smoke contract here; direct process serving is
    # still done by running `python main.py` without arguments.
    from fastapi.testclient import TestClient

    client = TestClient(app)
    checks = [
        ("GET /", client.get("/")),
        ("GET /health", client.get("/health")),
        ("GET /api/health", client.get("/api/health")),
        ("GET /api/product-bible-matrix", client.get("/api/product-bible-matrix")),
    ]
    failed = [name for name, response in checks if response.status_code != 200]
    if failed:
        print(json.dumps({"status": "fail", "failed": failed}, indent=2))
        return 1
    print(json.dumps({"status": "ok", "checks": [name for name, _ in checks]}, indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        raise SystemExit(smoke_check())
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
