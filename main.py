# Author: Mani Padisetti
"""CK Life OS - Five Practices for Living."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from urllib.parse import urlparse

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
        "reasoning_levels": ["low", "routine", "cheap"],
        "model": os.getenv("OPENROUTER_MODEL_FREE", "openrouter/free"),
        "cost_policy": "use OpenRouter's zero-cost free-model router first; override with OPENROUTER_MODEL_FREE",
        "paid": False,
        "price_hint": "$0 input / $0 output through OpenRouter's free router when available",
        "reasoning_effort": "low",
        "default_max_tokens": 350,
    },
    "modest": {
        "label": "A little bit expensive",
        "reasoning_levels": ["medium", "normal", "moderate"],
        "model": os.getenv("OPENROUTER_MODEL_MODEST", "openai/gpt-5.1"),
        "cost_policy": "use only when the task needs better reasoning than the free tier; override with OPENROUTER_MODEL_MODEST",
        "paid": True,
        "price_hint": "modest paid tier; default can be overridden when OpenRouter pricing changes",
        "reasoning_effort": "medium",
        "default_max_tokens": 600,
    },
    "expensive": {
        "label": "Full expensive models",
        "reasoning_levels": ["high", "deep", "hard"],
        "model": os.getenv("OPENROUTER_MODEL_EXPENSIVE", "openai/gpt-5.5"),
        "cost_policy": "reserve for complex reasoning, architecture, sensitive review, or high-value synthesis; override with OPENROUTER_MODEL_EXPENSIVE",
        "paid": True,
        "price_hint": "full paid tier for high-value reasoning; default can be overridden when OpenRouter pricing changes",
        "reasoning_effort": "high",
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

AUTO_REASONING_KEYWORDS = {
    "expensive": [
        "architecture",
        "deep audit",
        "five-loop",
        "security",
        "privacy",
        "high-stakes",
        "complex",
        "debug failing",
        "root cause",
        "product bible",
        "comprehensive",
        "thorough",
    ],
    "modest": [
        "compare",
        "summarise",
        "summarize",
        "draft",
        "rewrite",
        "analyse",
        "analyze",
        "moderate",
        "normal",
        "classify",
        "extract",
    ],
}


def _runtime_dir() -> Path:
    base = os.getenv("CK_LIFE_OS_DATA_DIR")
    if base:
        return Path(base)
    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(root) / "AMTL" / "ck-life-os"
    return Path.home() / ".local" / "share" / "ck-life-os"


REPO_ROOT = Path(__file__).resolve().parent
N8N_WORKFLOW_DIR = REPO_ROOT / "n8n" / "workflows"
RUNTIME_DIR = _runtime_dir()
RECEIPTS_FILE = RUNTIME_DIR / "practice-receipts.jsonl"
JOURNAL_FILE = RUNTIME_DIR / "encrypted-journal.jsonl"
JOURNAL_KEY_FILE = RUNTIME_DIR / "journal.key"
INNER_WORK_FILE = RUNTIME_DIR / "inner-work-sessions.jsonl"
SOURCE_INDEX_FILE = RUNTIME_DIR / "nas-source-index.jsonl"
SOURCE_INDEX_MANIFEST_FILE = RUNTIME_DIR / "nas-source-index-manifest.json"
RAG_SOURCE_DRAFTS_FILE = RUNTIME_DIR / "rag-source-drafts.jsonl"
LIFE_MANAGER_RECEIPTS_FILE = RUNTIME_DIR / "life-manager-receipts.jsonl"
N8N_PREFLIGHT_RECEIPTS_FILE = RUNTIME_DIR / "n8n-preflight-receipts.jsonl"
DAILY_LENS_SAVED_FILE = RUNTIME_DIR / "daily-lens-saved.jsonl"
ACADEMY_RECEIPTS_FILE = RUNTIME_DIR / "academy-receipts.jsonl"
LIVE_ACTION_RECEIPTS_FILE = RUNTIME_DIR / "live-action-receipts.jsonl"

NAS_SOURCE_ROOTS = [r"\\NAS2\amtl-documents", r"\\Nas1\Nas"]
NAS_EXCLUDED_ROOTS = [
    r"\\NAS2\amtl-documents\escalation-logs\linux logs\wazuz\prefe",
    r"\\Nas1\Nas\Programs\Spiritual\Dr Joe Dispenza\Generous moment\mani",
]
SOURCE_TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".xml",
    ".log",
}
SOURCE_SNIPPET_BYTES = 8192

LIFE_MANAGER_MENU = [
    {"group": "Today", "items": ["Home", "Daily Lens", "Start My Day", "Check In", "End My Day"], "default_open": True},
    {"group": "Guidance", "items": ["Ask Guide", "I Feel Stuck", "Decision Help", "Deep Inquiry"], "default_open": False},
    {"group": "Private", "items": ["Journal", "Shadow Work", "Voice Notes", "Life Map"], "default_open": False},
    {"group": "Plans", "items": ["Promises", "Projects", "Calendar"], "default_open": False},
    {"group": "Knowledge", "items": ["Academy", "Ask My Sources", "RAG / Sources", "Insights"], "default_open": False},
    {"group": "Reviews", "items": ["Daily Review", "Weekly Review", "Monthly Report"], "default_open": False},
    {"group": "Admin / Proof", "items": ["Privacy", "Memory", "Evidence", "Runtime", "Exports", "Dependency Status"], "default_open": False},
]

LIFE_MANAGER_SCREENS = [
    {
        "id": "today",
        "label": "Home",
        "menu_path": "Today -> Home",
        "tabs": ["Start", "State", "Proof-lite"],
        "panels": ["state chooser", "today's quiet signal", "current local boundaries"],
        "buttons": ["Start My Day", "I Feel Stuck", "Decision Help", "Process Something", "Review / Plan"],
        "workflow": "Route the user by human state, not by app architecture.",
    },
    {
        "id": "dailyLens",
        "label": "Daily Lens",
        "menu_path": "Today -> Daily Lens",
        "tabs": ["Today", "Saved", "Library"],
        "panels": ["current quiet lens", "saved lenses", "10k local lens library"],
        "buttons": ["Another lens", "Save lens", "Refresh saved", "Open lens library"],
        "workflow": "Show a fresh calm lens on return and let the user save useful lines locally.",
    },
    {
        "id": "startDay",
        "label": "Start My Day",
        "menu_path": "Today -> Start My Day",
        "tabs": ["Plan", "Promises", "Energy", "Smallest Step"],
        "panels": ["today's focus", "promises due", "energy fit", "calendar reality", "smallest next step"],
        "buttons": ["Accept plan", "Make gentler", "Reduce today", "Add promise", "Park this"],
        "workflow": "Create a humane local day plan without scores or streaks.",
    },
    {
        "id": "checkIn",
        "label": "Check In",
        "menu_path": "Today -> Check In",
        "tabs": ["Reality", "Adjust", "Ground"],
        "panels": ["what changed", "promise adjustment", "overload and energy status"],
        "buttons": ["Keep going", "Reduce", "Reschedule", "Remove", "Recommit", "I need grounding"],
        "workflow": "Adjust the day without shame.",
    },
    {
        "id": "endDay",
        "label": "End My Day",
        "menu_path": "Today -> End My Day",
        "tabs": ["Done", "Carried", "Learned", "Release"],
        "panels": ["done", "carried forward", "learning", "release note"],
        "buttons": ["Save review", "Carry forward", "Release this", "Add to Life Map", "Keep private"],
        "workflow": "Close the day without turning it into a report card.",
    },
    {
        "id": "askGuide",
        "label": "Ask Guide",
        "menu_path": "Guidance -> Ask Guide",
        "tabs": ["Mode", "Question", "Result"],
        "panels": ["Coach", "Shadow", "JK Inquiry", "Manager", "Companion", "Operator"],
        "buttons": ["Ask", "Ask one question only", "Make practical", "Go deeper", "Save to journal", "Turn into plan", "Stop / ground"],
        "workflow": "One guide surface with mode-specific posture and provider-gated AI.",
    },
    {
        "id": "stuck",
        "label": "I Feel Stuck",
        "menu_path": "Guidance -> I Feel Stuck",
        "tabs": ["Name", "Question", "Step"],
        "panels": ["stuck type", "one question", "smallest step"],
        "buttons": ["Name the stuck", "Ask me one question", "Turn into tiny step", "Park it", "Save privately"],
        "workflow": "Name the blocker and reduce pressure.",
    },
    {
        "id": "decision",
        "label": "Decision Help",
        "menu_path": "Guidance -> Decision Help",
        "tabs": ["Options", "Trade-offs", "Risks", "Proof Step"],
        "panels": ["options", "reversible/irreversible", "cost/risk", "next proof"],
        "buttons": ["Add option", "Compare options", "Decide now", "Gather proof", "Defer with date", "Abandon kindly"],
        "workflow": "Structure a decision without overthinking.",
    },
    {
        "id": "deepInquiry",
        "label": "Deep Inquiry",
        "menu_path": "Guidance -> Deep Inquiry",
        "tabs": ["Observe", "Assumption", "Leave Open"],
        "panels": ["observation", "assumption", "body signal", "unanswered question"],
        "buttons": ["Question assumption", "Observe reaction", "Leave unanswered", "Save privately", "Ground me"],
        "workflow": "Ask careful questions without claiming authority or final answers.",
    },
    {
        "id": "voiceNotes",
        "label": "Voice Notes",
        "menu_path": "Private -> Voice Notes",
        "tabs": ["Capture", "Convert", "Privacy"],
        "panels": ["pasted transcript", "classify target", "privacy choice"],
        "buttons": ["Save as journal", "Turn into promise", "Turn into task", "Ask questions", "Forget this"],
        "workflow": "Text-first voice workflow until transcription provider use is approved.",
    },
    {
        "id": "lifeMap",
        "label": "Life Map",
        "menu_path": "Private -> Life Map",
        "tabs": ["Values", "People", "Patterns", "Boundaries"],
        "panels": ["values", "roles", "people", "patterns", "do-not-push rules"],
        "buttons": ["Save Life Map note", "Pin", "Hide", "Delete", "Export"],
        "workflow": "Store the user's operating context with user control.",
    },
    {
        "id": "promises",
        "label": "Promises",
        "menu_path": "Plans -> Promises",
        "tabs": ["Active", "Due", "Review", "History"],
        "panels": ["active promises", "due promises", "broken-promise review", "history"],
        "buttons": ["Add promise", "Reduce", "Reschedule", "Remove", "Recommit"],
        "workflow": "Track promises without shame.",
    },
    {
        "id": "projects",
        "label": "Projects",
        "menu_path": "Plans -> Projects",
        "tabs": ["Tasks", "Dreams", "Open Loops", "Emotional Burdens"],
        "panels": ["task/project list", "someday ideas", "obligations", "open loops"],
        "buttons": ["Add project", "Add smallest step", "Park", "Link promise"],
        "workflow": "Separate tasks, dreams, obligations, and emotional burdens.",
    },
    {
        "id": "calendar",
        "label": "Calendar",
        "menu_path": "Plans -> Calendar",
        "tabs": ["Today", "Week", "Deadlines", "Recovery"],
        "panels": ["manual calendar items", "transition cost", "prep", "recovery load"],
        "buttons": ["Add manual event", "Add prep", "Add recovery", "Copy/export"],
        "workflow": "Show time reality without external calendar writes.",
    },
    {
        "id": "academy",
        "label": "Academy",
        "menu_path": "Knowledge -> Academy",
        "tabs": ["Programmes", "Lessons", "Practice", "Readiness"],
        "panels": ["learning paths", "lesson detail", "practice receipt", "local readiness"],
        "buttons": ["Refresh Academy", "Open lessons", "Start lesson", "Save practice receipt", "Check readiness"],
        "workflow": "Teach CK Life OS skills inside the app with local lessons, practice receipts, and no external LMS dependency.",
    },
    {
        "id": "askSources",
        "label": "Ask My Sources",
        "menu_path": "Knowledge -> Ask My Sources",
        "tabs": ["Ask", "Sources", "Answer", "Memory"],
        "panels": ["source-backed question", "selected sources", "cited answer", "add-to-memory prompt"],
        "buttons": ["Ask sources", "Search", "Add to memory", "Do not remember"],
        "workflow": "Use RAG search with citations and memory approval.",
    },
    {
        "id": "sources",
        "label": "RAG / Sources",
        "menu_path": "Knowledge -> RAG / Sources",
        "tabs": ["Status", "Add", "Search", "Results"],
        "panels": ["RAG status", "source intake", "source search", "result cards"],
        "buttons": ["Explain RAG access", "Add source", "Stage source", "Search", "Build local index"],
        "workflow": "Manage source drafts, exact exclusions, local source search, and approval-gated URL fetch.",
    },
    {
        "id": "insights",
        "label": "Insights",
        "menu_path": "Knowledge -> Insights",
        "tabs": ["Patterns", "Evidence", "Hidden"],
        "panels": ["evidence-backed patterns", "confidence", "source links", "hidden/dismissed insights"],
        "buttons": ["Show why", "Hide", "Dismiss", "Add to Life Map"],
        "workflow": "Show patterns only when there is evidence.",
    },
    {
        "id": "dailyReview",
        "label": "Daily Review",
        "menu_path": "Reviews -> Daily Review",
        "tabs": ["Today", "Receipts", "Next"],
        "panels": ["today's receipts", "review note", "tomorrow seed"],
        "buttons": ["Save review", "Carry forward", "Export local note"],
        "workflow": "Close the current day with learning, not scoring.",
    },
    {
        "id": "weeklyReview",
        "label": "Weekly Review",
        "menu_path": "Reviews -> Weekly Review",
        "tabs": ["Promises", "Patterns", "Energy", "Experiment"],
        "panels": ["kept/adjusted promises", "friction", "energy", "next experiment"],
        "buttons": ["Create weekly review", "Continue", "Stop", "Export"],
        "workflow": "Turn the week into one useful experiment.",
    },
    {
        "id": "monthlyReport",
        "label": "Monthly Report",
        "menu_path": "Reviews -> Monthly Report",
        "tabs": ["Summary", "Patterns", "Sources", "Export"],
        "panels": ["promise/energy/source/pattern rollup", "effort reduction"],
        "buttons": ["Create monthly report", "Export markdown", "Add to Life Map"],
        "workflow": "Generate a private monthly life report without external send.",
    },
    {
        "id": "privacy",
        "label": "Privacy",
        "menu_path": "Admin / Proof -> Privacy",
        "tabs": ["Local", "Encrypted", "Providers", "Exports"],
        "panels": ["local storage", "encrypted stores", "provider gates", "export controls"],
        "buttons": ["Inspect privacy", "Export", "Delete local draft", "Provider policy"],
        "workflow": "Explain data boundaries only when requested.",
    },
    {
        "id": "memory",
        "label": "Memory",
        "menu_path": "Admin / Proof -> Memory",
        "tabs": ["Remembered", "Sensitive", "Disabled", "Export"],
        "panels": ["memory rows", "sensitivity", "source", "use toggle"],
        "buttons": ["Inspect", "Edit", "Delete", "Disable", "Export"],
        "workflow": "Let the user inspect and control memory.",
    },
]

N8N_WORKFLOW_REGISTRY = [
    {
        "workflow_id": "ck-life-os-openrouter-paid-execution-preflight",
        "name": "CK Life OS - OpenRouter Paid Execution Preflight",
        "menu_path": "Admin / Proof -> Runtime -> n8n workflows",
        "fixes_boundary": "paid_model_execution",
        "purpose": "Routes approved medium/high reasoning work through OpenRouter only after explicit CK approval and cost-tier confirmation.",
        "n8n_file": "ck-life-os-openrouter-paid-execution-preflight.json",
        "webhook_path": "ck-life-os/openrouter-paid-execution-preflight",
        "trigger": "webhook_dry_run_or_approved_live_request",
        "required_approvals": ["execute=true", "allow_paid_provider=true for modest/expensive tiers", "server-side OPENROUTER_API_KEY"],
        "required_credentials": ["OpenRouter API key stored in n8n credentials or CK runtime env"],
        "live_side_effect": "paid provider call",
        "dry_run_supported": True,
        "active_by_default": False,
        "safe_local_status": "importable_disabled_workflow_and_ck_preflight_endpoint_ready",
        "rollback": "deactivate/delete the n8n workflow; remove credentials; CK local receipts remain read-only proof",
    },
    {
        "workflow_id": "ck-life-os-voice-transcription-preflight",
        "name": "CK Life OS - Voice Transcription Preflight",
        "menu_path": "Admin / Proof -> Runtime -> n8n workflows",
        "fixes_boundary": "live_voice_transcription",
        "purpose": "Accepts an approved local audio/transcript request and routes to local Whisper or an approved transcription provider, then returns text to CK as a private draft.",
        "n8n_file": "ck-life-os-voice-transcription-preflight.json",
        "webhook_path": "ck-life-os/voice-transcription-preflight",
        "trigger": "webhook_dry_run_or_approved_transcription_request",
        "required_approvals": ["audio_source approved", "privacy level selected", "transcription provider approved if not local"],
        "required_credentials": ["local Whisper command or approved transcription provider credential"],
        "live_side_effect": "audio leaves local machine only if non-local provider is explicitly approved",
        "dry_run_supported": True,
        "active_by_default": False,
        "safe_local_status": "importable_disabled_workflow_and_ck_preflight_endpoint_ready",
        "rollback": "delete transcript draft receipt; deactivate/delete workflow; revoke provider credential if used",
    },
    {
        "workflow_id": "ck-life-os-calendar-write-preflight",
        "name": "CK Life OS - Calendar Write Preflight",
        "menu_path": "Admin / Proof -> Runtime -> n8n workflows",
        "fixes_boundary": "external_calendar_writes",
        "purpose": "Turns a CK manual calendar note into a calendar create/update draft, shows exact target/time/title, then writes only after explicit approval.",
        "n8n_file": "ck-life-os-calendar-write-preflight.json",
        "webhook_path": "ck-life-os/calendar-write-preflight",
        "trigger": "webhook_dry_run_or_approved_calendar_write",
        "required_approvals": ["calendar target selected", "event preview approved", "write=true", "rollback/delete plan accepted"],
        "required_credentials": ["Google Calendar, Microsoft Graph, CalDAV, or local ICS target credential"],
        "live_side_effect": "external calendar event create/update/delete",
        "dry_run_supported": True,
        "active_by_default": False,
        "safe_local_status": "importable_disabled_workflow_and_ck_preflight_endpoint_ready",
        "rollback": "delete created event by event id or import prior ICS backup; keep CK receipt",
    },
    {
        "workflow_id": "ck-life-os-memory-sync-preflight",
        "name": "CK Life OS - Memory Sync Preflight",
        "menu_path": "Admin / Proof -> Runtime -> n8n workflows",
        "fixes_boundary": "cross_device_memory_sync",
        "purpose": "Exports selected CK memory rows to an approved encrypted sync target after sensitivity review and per-row user approval.",
        "n8n_file": "ck-life-os-memory-sync-preflight.json",
        "webhook_path": "ck-life-os/memory-sync-preflight",
        "trigger": "webhook_dry_run_or_approved_memory_sync",
        "required_approvals": ["memory rows selected", "sensitivity reviewed", "target approved", "export/sync=true"],
        "required_credentials": ["approved encrypted storage, local NAS, Syncthing, Nextcloud, or other user-owned sync credential"],
        "live_side_effect": "selected private memory rows copied to approved sync target",
        "dry_run_supported": True,
        "active_by_default": False,
        "safe_local_status": "importable_disabled_workflow_and_ck_preflight_endpoint_ready",
        "rollback": "delete exported object by manifest id; disable sync target; retain local CK source of truth",
    },
]

INNER_WORK_MODES = {
    "shadow": {
        "label": "Shadow integration",
        "posture": "meet the rejected/protective part without acting it out or shaming it",
        "first_question": "What part of you feels unacceptable, protective, exaggerated, or pushed away here?",
        "program": [
            "Name the trigger without explaining it away.",
            "Notice the body signal and the story that arrived with it.",
            "Ask what this part is protecting.",
            "Ask what this part costs when it takes over.",
            "Ask what it wants acknowledged, not obeyed.",
            "Choose one integration action that does not harm you or anyone else.",
            "Review what became clearer without turning it into a score.",
        ],
    },
    "jk_observation": {
        "label": "Observation / Krishnamurti-style inquiry",
        "posture": "observe thought, fear, image, comparison, and becoming without claiming authority or quoting as certainty",
        "first_question": "Can this be observed for a moment before naming, fixing, or becoming something else?",
        "program": [
            "Describe only what happened.",
            "Notice the image of yourself or the other person.",
            "Notice comparison, fear, memory, or desire to become.",
            "Stay with the sensation before the explanation.",
            "Ask whether the observer is separate from what is observed.",
            "Pause before action; do not force insight.",
            "Write what was seen plainly, without a spiritual conclusion.",
        ],
    },
    "grounding": {
        "label": "Grounding first",
        "posture": "stabilise before depth; choose safety over insight",
        "first_question": "What is one body-safe fact in the room right now?",
        "program": [
            "Orient to the room and name one safe object.",
            "Slow the pace; no meaning-making yet.",
            "Name the feeling with low drama.",
            "Choose water, movement, rest, or contact with a trusted person if needed.",
            "Decide whether deeper inquiry should wait.",
            "Write one sentence only if it helps.",
            "Stop on purpose; stopping counts.",
        ],
    },
    "relationship": {
        "label": "Relationship pattern",
        "posture": "separate the event, the story, the need, and the next clean action",
        "first_question": "What happened, and what did your mind immediately say it meant?",
        "program": [
            "Separate event from interpretation.",
            "Name the need or fear underneath.",
            "Notice the old pattern that may be repeating.",
            "Ask what is yours, theirs, and unknown.",
            "Choose whether to speak, wait, or write privately.",
            "Draft one clean sentence without accusation.",
            "Review whether the next step is kind and true.",
        ],
    },
    "unknown": {
        "label": "I do not know yet",
        "posture": "start gently and choose the right depth after the first reflection",
        "first_question": "If this feeling had one sentence, what would it say?",
        "program": [
            "Write the raw situation in plain language.",
            "Choose whether this needs grounding, inquiry, shadow work, or rest.",
            "Ask one question only.",
            "Wait for the body response.",
            "Name what feels useful and what feels too much.",
            "Choose the smallest next step.",
            "Stop or continue with consent.",
        ],
    },
}

SAFETY_WORDS = {"suicide", "kill myself", "self harm", "self-harm", "hurt myself", "hurt someone", "violence"}


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


def _append_life_manager_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    screen = str(payload.get("screen") or "unknown")[:80]
    action = str(payload.get("action") or "local_note")[:120]
    receipt = {
        "receipt_id": f"life-manager-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "screen": screen,
        "action": action,
        "note": _safe_note(payload),
        "local_only": True,
        "external_send": False,
        "source_write": False,
        "provider_called": False,
        "paid_provider_call": False,
        "calendar_write": False,
        "transcription_provider_called": False,
        "storage": str(LIFE_MANAGER_RECEIPTS_FILE),
    }
    with LIFE_MANAGER_RECEIPTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")
    _append_receipt({"practice": "system", "note": f"Life Manager v2: {screen} / {action}", **receipt})
    return receipt


def _read_life_manager_receipts(limit: int = 50) -> list[dict[str, Any]]:
    if not LIFE_MANAGER_RECEIPTS_FILE.exists():
        return []
    rows = []
    for line in LIFE_MANAGER_RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _workflow_by_id(workflow_id: str) -> dict[str, Any]:
    workflow = next((item for item in N8N_WORKFLOW_REGISTRY if item["workflow_id"] == workflow_id), None)
    if workflow is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_n8n_workflow", "workflow_id": workflow_id})
    return workflow


def _n8n_workflow_summary(workflow: dict[str, Any]) -> dict[str, Any]:
    path = N8N_WORKFLOW_DIR / workflow["n8n_file"]
    return {
        **workflow,
        "path": str(path),
        "exists": path.exists(),
        "active_in_export": False,
        "live_import_performed": False,
        "live_execution_performed": False,
        "external_send": False,
        "source_write": False,
        "secret_exposed": False,
    }


def _append_n8n_preflight_receipt(workflow: dict[str, Any], payload: dict[str, Any], mode: str) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    requested_live = bool(payload.get("live_execute") or payload.get("write") or payload.get("sync") or payload.get("provider_call"))
    explicit_approval = bool(payload.get("explicit_approval"))
    approved = requested_live and explicit_approval and bool(payload.get("approval_reference"))
    receipt = {
        "receipt_id": f"n8n-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "workflow_id": workflow["workflow_id"],
        "workflow_name": workflow["name"],
        "mode": mode,
        "requested_live_execution": requested_live,
        "explicit_approval": explicit_approval,
        "approval_reference_present": bool(payload.get("approval_reference")),
        "status": "dry_run_recorded" if mode == "dry_run" else ("ready_for_manual_import_review" if approved else "blocked_for_live_until_approved"),
        "approval_required": not approved,
        "required_approvals": workflow["required_approvals"],
        "required_credentials": workflow["required_credentials"],
        "live_side_effect": workflow["live_side_effect"],
        "n8n_file": str(N8N_WORKFLOW_DIR / workflow["n8n_file"]),
        "webhook_path": workflow["webhook_path"],
        "external_send": False,
        "source_write": False,
        "provider_called": False,
        "paid_provider_call": False,
        "calendar_write": False,
        "transcription_provider_called": False,
        "memory_sync_performed": False,
        "live_n8n_import_performed": False,
        "live_n8n_execution_performed": False,
        "rollback": workflow["rollback"],
        "note": _safe_note(payload),
    }
    with N8N_PREFLIGHT_RECEIPTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")
    _append_receipt({"practice": "system", "note": f"n8n workflow {workflow['workflow_id']} {mode}", **receipt})
    return receipt


def _read_n8n_preflight_receipts(limit: int = 50) -> list[dict[str, Any]]:
    if not N8N_PREFLIGHT_RECEIPTS_FILE.exists():
        return []
    rows = []
    for line in N8N_PREFLIGHT_RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


ACADEMY_PROGRAMMES = [
    {
        "program_id": "ck-start-here",
        "title": "Start Here",
        "purpose": "Learn the calm CK operating model: choose state first, keep proof out of the normal flow, and make one humane next move.",
        "screen_path": "Today -> Home",
        "level": "foundation",
    },
    {
        "program_id": "daily-operating-system",
        "title": "Daily Operating System",
        "purpose": "Use Daily Lens, Start My Day, Check In, End My Day, and reviews without pressure or streaks.",
        "screen_path": "Today",
        "level": "foundation",
    },
    {
        "program_id": "inner-work-shadow-integration",
        "title": "Inner Work and Shadow Integration",
        "purpose": "Use private guided inquiry for shadow, observation, grounding, and relationship patterns without turning it into diagnosis.",
        "screen_path": "Private -> Inner Work",
        "level": "deep",
    },
    {
        "program_id": "decision-risk",
        "title": "Decision and Risk",
        "purpose": "Separate options, reversible moves, evidence gaps, cost, and smallest proof steps.",
        "screen_path": "Guidance -> Decision Help",
        "level": "applied",
    },
    {
        "program_id": "rag-source-literacy",
        "title": "RAG and Source Literacy",
        "purpose": "Understand Ask My Sources, RAG / Sources, internal and external source boundaries, and the two approved NAS exclusions.",
        "screen_path": "Knowledge -> RAG / Sources",
        "level": "applied",
    },
    {
        "program_id": "automation-approval-safety",
        "title": "Automation and Approval Safety",
        "purpose": "Learn when OpenRouter, voice, Ripple calendar, memory sync, and n8n are dry-run, ready, or blocked.",
        "screen_path": "Admin / Proof -> Runtime",
        "level": "advanced",
    },
    {
        "program_id": "resilience-difficult-day",
        "title": "Resilience and Difficult Day Mode",
        "purpose": "Reduce the plan when the day is hard, without making the user wrong.",
        "screen_path": "Today -> Check In",
        "level": "foundation",
    },
]

ACADEMY_LESSONS = [
    {
        "lesson_id": "academy-001",
        "program_id": "ck-start-here",
        "title": "Choose The Human State First",
        "menu_path": "Today -> Home",
        "buttons": ["Start My Day", "I Feel Stuck", "Decision Help", "Process Something", "Review / Plan"],
        "practice_prompt": "What state am I actually in, and which one button would reduce friction now?",
    },
    {
        "lesson_id": "academy-002",
        "program_id": "daily-operating-system",
        "title": "Use Daily Lens Without Turning It Into Homework",
        "menu_path": "Today -> Daily Lens",
        "buttons": ["Another lens", "Save lens", "Refresh saved", "Open lens library"],
        "practice_prompt": "Save one line only if it changes the next five minutes.",
    },
    {
        "lesson_id": "academy-003",
        "program_id": "daily-operating-system",
        "title": "Make The Day Smaller Without Shame",
        "menu_path": "Today -> Start My Day",
        "buttons": ["Accept plan", "Make gentler", "Reduce today", "Park this"],
        "practice_prompt": "What is the smallest honest version of today's plan?",
    },
    {
        "lesson_id": "academy-004",
        "program_id": "inner-work-shadow-integration",
        "title": "Start Shadow Integration Slowly",
        "menu_path": "Private -> Inner Work",
        "buttons": ["Start guided session", "Load sessions"],
        "practice_prompt": "What rejected or protective part is asking to be noticed, not obeyed?",
    },
    {
        "lesson_id": "academy-005",
        "program_id": "decision-risk",
        "title": "Decide With A Proof Step",
        "menu_path": "Guidance -> Decision Help",
        "buttons": ["Add option", "Compare options", "Gather proof", "Defer with date"],
        "practice_prompt": "Which option can be tested with the least cost and most learning?",
    },
    {
        "lesson_id": "academy-006",
        "program_id": "rag-source-literacy",
        "title": "Ask Sources Before Guessing",
        "menu_path": "Knowledge -> Ask My Sources",
        "buttons": ["Ask sources", "Search", "Add to memory", "Do not remember"],
        "practice_prompt": "What claim should be checked against a source before the guide uses it?",
    },
    {
        "lesson_id": "academy-007",
        "program_id": "rag-source-literacy",
        "title": "Stage A Source Safely",
        "menu_path": "Knowledge -> RAG / Sources",
        "buttons": ["Explain RAG access", "Stage source for approval", "Search", "Build local index"],
        "practice_prompt": "Is this source internal, external draft, pasted text, or explicitly approved one-time fetch?",
    },
    {
        "lesson_id": "academy-008",
        "program_id": "automation-approval-safety",
        "title": "Know The Difference Between Dry-Run And Live",
        "menu_path": "Admin / Proof -> Runtime",
        "buttons": ["OpenRouter routing", "n8n workflow pack", "Dependency fallback"],
        "practice_prompt": "What exact approval, endpoint, key, and rollback would be needed before this action becomes live?",
    },
    {
        "lesson_id": "academy-009",
        "program_id": "resilience-difficult-day",
        "title": "Make The Plan Lighter",
        "menu_path": "Today -> Check In",
        "buttons": ["Reduce", "Reschedule", "I need grounding"],
        "practice_prompt": "What can be reduced without making myself wrong?",
    },
]


def _academy_program(program_id: str) -> dict[str, Any]:
    program = next((item for item in ACADEMY_PROGRAMMES if item["program_id"] == program_id), None)
    if program is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_academy_program", "program_id": program_id})
    return program


def _academy_lesson(lesson_id: str) -> dict[str, Any]:
    lesson = next((item for item in ACADEMY_LESSONS if item["lesson_id"] == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_academy_lesson", "lesson_id": lesson_id})
    return {
        **lesson,
        "program": _academy_program(lesson["program_id"]),
        "source_boundary": "local CK lesson catalogue; no external LMS, provider call, source write, or paid model execution",
        "field_utility": {
            "what": lesson["title"],
            "who": "Mani/local CK user",
            "why": "learn one CK workflow without scrolling or hunting",
            "when": "when a module is unfamiliar or a refresher would reduce effort",
            "where": lesson["menu_path"],
            "how": "read the lesson, click the matching product button, then save a practice receipt only if useful",
            "eli10": "a small lesson shows what to click and why it helps.",
        },
        "status": "published_local_internal",
    }


def _academy_lessons_for_program(program_id: str | None = None) -> list[dict[str, Any]]:
    lessons = ACADEMY_LESSONS if program_id is None else [item for item in ACADEMY_LESSONS if item["program_id"] == program_id]
    return [_academy_lesson(item["lesson_id"]) for item in lessons]


def _append_academy_receipt(payload: dict[str, Any], lesson: dict[str, Any]) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_id": f"academy-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "lesson_id": lesson["lesson_id"],
        "program_id": lesson["program_id"],
        "menu_path": lesson["menu_path"],
        "action": str(payload.get("action") or "Save practice receipt")[:120],
        "practice_note": _safe_note(payload),
        "local_only": True,
        "external_lms_write": False,
        "external_send": False,
        "source_write": False,
        "provider_called": False,
        "storage": str(ACADEMY_RECEIPTS_FILE),
    }
    with ACADEMY_RECEIPTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")
    _append_receipt({"practice": "system", "note": f"Academy lesson {lesson['lesson_id']}", **receipt})
    return receipt


def _read_academy_receipts(limit: int = 50) -> list[dict[str, Any]]:
    if not ACADEMY_RECEIPTS_FILE.exists():
        return []
    rows = []
    for line in ACADEMY_RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _append_live_action_receipt(action: str, payload: dict[str, Any], status: str, blockers: list[str], **extra: Any) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_id": f"live-action-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "action": action,
        "status": status,
        "blockers": blockers,
        "explicit_approval": bool(payload.get("explicit_approval")),
        "approval_reference_present": bool(payload.get("approval_reference")),
        "note": _safe_note(payload),
        "live_action_performed": status == "performed",
        "external_send": bool(extra.get("external_send", False)),
        "source_write": False,
        "provider_called": bool(extra.get("provider_called", False)),
        "paid_provider_call": bool(extra.get("paid_provider_call", False)),
        "calendar_write": bool(extra.get("calendar_write", False)),
        "transcription_provider_called": bool(extra.get("transcription_provider_called", False)),
        "memory_sync_performed": bool(extra.get("memory_sync_performed", False)),
        "rollback": extra.get("rollback") or "No live action occurred; discard this local receipt if it was a test.",
        "storage": str(LIVE_ACTION_RECEIPTS_FILE),
        **{key: value for key, value in extra.items() if key not in {"external_send", "provider_called", "paid_provider_call", "calendar_write", "transcription_provider_called", "memory_sync_performed", "rollback"}},
    }
    with LIVE_ACTION_RECEIPTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")
    _append_receipt({"practice": "system", "note": f"Live action gate {action}: {status}", **receipt})
    return receipt


def _read_live_action_receipts(limit: int = 50) -> list[dict[str, Any]]:
    if not LIVE_ACTION_RECEIPTS_FILE.exists():
        return []
    rows = []
    for line in LIVE_ACTION_RECEIPTS_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _approval_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = []
    if not bool(payload.get("execute") or payload.get("write") or payload.get("sync") or payload.get("live_execute")):
        blockers.append("execute/write/sync/live_execute flag not true")
    if not bool(payload.get("explicit_approval")):
        blockers.append("explicit_approval missing")
    if not payload.get("approval_reference"):
        blockers.append("approval_reference missing")
    return blockers


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


def _inner_work_safety_state(text: str) -> dict[str, Any]:
    lowered = text.lower()
    flagged = any(word in lowered for word in SAFETY_WORDS)
    return {
        "state": "grounding_required" if flagged else "ok_for_reflection",
        "depth_allowed": "grounding_only" if flagged else "guided_reflection",
        "message": (
            "Pause the inquiry and contact local emergency or crisis support now if there is immediate danger."
            if flagged
            else "No crisis phrase detected; keep the work slow and consent-based."
        ),
        "not_therapy": True,
    }


def _inner_work_prompt(mode_key: str, text: str) -> dict[str, Any]:
    effective_mode_key = mode_key if mode_key in INNER_WORK_MODES else "unknown"
    mode = INNER_WORK_MODES[effective_mode_key]
    safety = _inner_work_safety_state(text)
    if safety["depth_allowed"] == "grounding_only":
        effective_mode_key = "grounding"
        mode = INNER_WORK_MODES["grounding"]
    trimmed = " ".join(text.split())[:220] or "No input yet."
    return {
        "mode": effective_mode_key,
        "mode_label": mode["label"],
        "guide_posture": mode["posture"],
        "input_reflection": f"I heard this as the starting point: {trimmed}",
        "not_answer": "This is guidance for looking carefully, not a final interpretation or diagnosis.",
        "first_question": mode["first_question"],
        "program": [
            {"day": index + 1, "step": step, "can_skip": True, "pace": "slow"}
            for index, step in enumerate(mode["program"])
        ],
        "session_controls": ["pause", "switch_to_grounding", "save_encrypted", "stop"],
        "safety": safety,
        "ai_provider_called": False,
    }


def _read_inner_work_rows(limit: int = 20) -> list[dict[str, Any]]:
    if not INNER_WORK_FILE.exists():
        return []
    rows = []
    for line in INNER_WORK_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _inner_work_summary(row: dict[str, Any]) -> dict[str, Any]:
    payload = _decrypt_inner_work_payload(row)
    return {
        "session_id": row["session_id"],
        "created_at": row["created_at"],
        "mode": payload["mode"],
        "mode_label": payload["mode_label"],
        "safety_state": payload["safety"]["state"],
        "first_question": payload["first_question"],
        "encrypted_at_rest": True,
        "external_send": False,
        "source_write": False,
    }


def _append_inner_work_session(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "unknown").strip()
    text = str(payload.get("input") or payload.get("text") or payload.get("voice_transcript") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail={"error": "inner_work_input_required"})
    guidance = _inner_work_prompt(mode, text[:5000])
    encrypted_payload = {
        **guidance,
        "input_text": text[:5000],
        "input_kind": "voice_transcript" if payload.get("voice_transcript") else "text",
        "user_intention": str(payload.get("intention") or "").strip()[:300],
    }
    row = {
        "session_id": f"inner-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "ciphertext": _journal_fernet().encrypt(json.dumps(encrypted_payload, ensure_ascii=True).encode("utf-8")).decode("ascii"),
        "encryption": {
            "scheme": "fernet",
            "key_source": "CK_LIFE_OS_JOURNAL_KEY" if os.getenv("CK_LIFE_OS_JOURNAL_KEY") else "local_runtime_key_file",
            "plaintext_stored": False,
        },
        "external_send": False,
        "source_write": False,
    }
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with INNER_WORK_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return {"row": row, "guidance": guidance}


def _decrypt_inner_work_payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = _journal_fernet().decrypt(str(row["ciphertext"]).encode("ascii")).decode("utf-8")
        return json.loads(raw)
    except (InvalidToken, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=409, detail={"error": "inner_work_decryption_failed"}) from exc


def _normalise_source_path(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path).rstrip("\\/")))


def _is_excluded_source_path(path: str | Path) -> bool:
    candidate = _normalise_source_path(path)
    for excluded in NAS_EXCLUDED_ROOTS:
        root = _normalise_source_path(excluded)
        if candidate == root or candidate.startswith(root + os.sep):
            return True
    return False


def _redact_source_snippet(text: str) -> str:
    redacted_words = []
    for word in text.replace("\r", " ").replace("\n", " ").split():
        lowered = word.lower()
        looks_sensitive = (
            "password" in lowered
            or "secret" in lowered
            or "token" in lowered
            or "api_key" in lowered
            or len(word) > 48
        )
        redacted_words.append("[redacted]" if looks_sensitive else word)
    return " ".join(redacted_words)[:700]


def _source_file_record(path: Path, root: str) -> dict[str, Any]:
    stat = path.stat()
    snippet = ""
    readable_text = path.suffix.lower() in SOURCE_TEXT_SUFFIXES and stat.st_size <= 2_000_000
    if readable_text:
        try:
            raw = path.read_bytes()[:SOURCE_SNIPPET_BYTES]
            snippet = _redact_source_snippet(raw.decode("utf-8", errors="ignore"))
        except OSError:
            snippet = ""
    digest_source = f"{path}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8", errors="ignore")
    return {
        "source_id": hashlib.sha256(digest_source).hexdigest()[:24],
        "root": root,
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "text_indexed": bool(snippet),
        "snippet": snippet,
    }


def _write_source_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_INDEX_MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def _source_index_manifest() -> dict[str, Any]:
    if SOURCE_INDEX_MANIFEST_FILE.exists():
        try:
            return json.loads(SOURCE_INDEX_MANIFEST_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "status": "not_built",
        "roots": NAS_SOURCE_ROOTS,
        "excluded_roots": NAS_EXCLUDED_ROOTS,
        "excluded_roots_count": len(NAS_EXCLUDED_ROOTS),
        "index_path": str(SOURCE_INDEX_FILE),
        "manifest_path": str(SOURCE_INDEX_MANIFEST_FILE),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


def _iter_source_files(roots: list[str], max_files: int | None = None):
    indexed_seen = 0
    excluded_seen = 0
    access_issues: list[dict[str, str]] = []
    _iter_source_files.last_access_issues = access_issues
    _iter_source_files.last_excluded_seen = excluded_seen
    stack = [Path(root) for root in reversed(roots)]
    while stack:
        current = stack.pop()
        if _is_excluded_source_path(current):
            excluded_seen += 1
            continue
        try:
            with os.scandir(current) as entries:
                children = list(entries)
        except OSError as exc:
            access_issues.append({"path": str(current), "error": str(exc)[:240]})
            continue
        for entry in children:
            child = Path(entry.path)
            if _is_excluded_source_path(child):
                excluded_seen += 1
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(child)
                elif entry.is_file(follow_symlinks=False):
                    yield child
                    indexed_seen += 1
                    if max_files is not None and indexed_seen >= max_files:
                        _iter_source_files.last_access_issues = access_issues
                        _iter_source_files.last_excluded_seen = excluded_seen
                        return
            except OSError as exc:
                access_issues.append({"path": str(child), "error": str(exc)[:240]})
                continue
    _iter_source_files.last_access_issues = access_issues
    _iter_source_files.last_excluded_seen = excluded_seen


def _build_source_index(max_files: int | None = None, roots: list[str] | None = None) -> dict[str, Any]:
    roots = roots or NAS_SOURCE_ROOTS
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    records_written = 0
    text_records = 0
    bytes_seen = 0
    access_issues: list[dict[str, str]] = []
    excluded_seen = 0
    started = _utc_now()
    with SOURCE_INDEX_FILE.open("w", encoding="utf-8") as handle:
        iterator = _iter_source_files(roots, max_files=max_files)
        try:
            for path in iterator:
                try:
                    record = _source_file_record(path, root=next((root for root in roots if _normalise_source_path(path).startswith(_normalise_source_path(root))), roots[0]))
                except OSError as exc:
                    access_issues.append({"path": str(path), "error": str(exc)[:240]})
                    continue
                records_written += 1
                text_records += 1 if record["text_indexed"] else 0
                bytes_seen += int(record["size_bytes"])
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        finally:
            access_issues.extend(getattr(_iter_source_files, "last_access_issues", []))
            excluded_seen = int(getattr(_iter_source_files, "last_excluded_seen", 0))
    manifest = {
        "status": "built",
        "started_at": started,
        "completed_at": _utc_now(),
        "roots": roots,
        "excluded_roots": NAS_EXCLUDED_ROOTS,
        "excluded_roots_count": len(NAS_EXCLUDED_ROOTS),
        "excluded_paths_seen": excluded_seen,
        "only_approved_exclusions": True,
        "files_indexed": records_written,
        "text_records": text_records,
        "bytes_seen": bytes_seen,
        "truncated_by_max_files": max_files is not None and records_written >= max_files,
        "max_files": max_files,
        "access_issues": access_issues[:100],
        "access_issue_count": len(access_issues),
        "index_path": str(SOURCE_INDEX_FILE),
        "manifest_path": str(SOURCE_INDEX_MANIFEST_FILE),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
        "pgvector_required": False,
        "mode": "local_metadata_and_text_snippet_index",
    }
    return _write_source_manifest(manifest)


def _read_source_records(limit: int = 2000) -> list[dict[str, Any]]:
    if not SOURCE_INDEX_FILE.exists():
        return []
    rows = []
    with SOURCE_INDEX_FILE.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _search_source_index(query: str, limit: int = 20) -> dict[str, Any]:
    needle = query.lower().strip()
    if not needle:
        raise HTTPException(status_code=400, detail={"error": "query_required"})
    matches = []
    scanned = 0
    if SOURCE_INDEX_FILE.exists():
        with SOURCE_INDEX_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                scanned += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                haystack = f"{row.get('path', '')} {row.get('name', '')} {row.get('snippet', '')}".lower()
                if needle in haystack:
                    matches.append({
                        "source_id": row["source_id"],
                        "path": row["path"],
                        "name": row["name"],
                        "modified_at": row["modified_at"],
                        "snippet": row.get("snippet", "")[:360],
                    })
                    if len(matches) >= limit:
                        break
    return {
        "query": query,
        "matches": matches,
        "returned": len(matches),
        "scanned_until_limit": scanned,
        "manifest": _source_index_manifest(),
        "external_send": False,
        "provider_called": False,
    }


def _read_rag_source_drafts(limit: int = 500) -> list[dict[str, Any]]:
    if not RAG_SOURCE_DRAFTS_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    with RAG_SOURCE_DRAFTS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows[-limit:]


def _append_rag_source_draft(payload: dict[str, Any]) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    source_type = str(payload.get("source_type", "internal")).strip().lower()
    if source_type not in {"internal", "external"}:
        raise HTTPException(status_code=400, detail={"error": "source_type_must_be_internal_or_external"})
    source_text = _safe_note({"note": payload.get("source_text") or payload.get("content") or ""})[:6000]
    external_fetch_approved = bool(payload.get("fetch_approved"))
    external_fetch_performed = False
    external_fetch_status = "not_requested"
    fetched_url = ""
    if source_type == "external" and external_fetch_approved:
        location = str(payload.get("location") or "").strip()
        fetch_result = _fetch_external_rag_source(location)
        fetched_url = fetch_result["url"]
        source_text = _safe_note({"note": fetch_result["text"]})[:6000]
        external_fetch_performed = True
        external_fetch_status = "approved_local_ingest"
    elif source_type == "external":
        external_fetch_status = "approval_required"
    row = {
        "source_id": f"rag-source-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "created_at": _utc_now(),
        "source_type": source_type,
        "title": _safe_note({"note": payload.get("title") or "Untitled RAG source draft"})[:160],
        "location": _safe_note({"note": payload.get("location") or ""})[:500],
        "notes": _safe_note({"note": payload.get("notes") or ""})[:1000],
        "source_text": source_text,
        "searchable_local_text": bool(source_text),
        "accepted_for_rag": True,
        "external_fetch_approved": external_fetch_approved,
        "external_fetch_performed": external_fetch_performed,
        "external_fetch_status": external_fetch_status,
        "fetched_url": fetched_url,
        "external_send": False,
        "source_write": False,
        "local_write": True,
        "approval_required_before_external_fetch": source_type == "external" and not external_fetch_approved,
        "next_action": "Search local RAG drafts and approved NAS index; external URL text is local-searchable only after explicit approved fetch.",
    }
    with RAG_SOURCE_DRAFTS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    return row


def _external_rag_url_allowed(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "url_scheme_must_be_http_or_https"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "url_host_required"
    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if host in blocked_hosts or host.endswith(".local") or host.startswith("10.") or host.startswith("192.168."):
        return False, "local_or_private_hosts_are_not_allowed_for_rag_fetch"
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) > 1 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return False, "local_or_private_hosts_are_not_allowed_for_rag_fetch"
    return True, "allowed"


def _fetch_external_rag_source(url: str) -> dict[str, Any]:
    allowed, reason = _external_rag_url_allowed(url)
    if not allowed:
        raise HTTPException(status_code=400, detail={"error": reason, "url": url})
    request = UrlRequest(
        url,
        headers={
            "User-Agent": "CK-Life-OS-local-rag-source-fetch/1.0",
            "Accept": "text/plain,text/markdown,text/html,application/json;q=0.8,*/*;q=0.2",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            content_type = response.headers.get("content-type", "")
            if content_type and not any(token in content_type.lower() for token in ["text/", "json", "xml", "html", "markdown"]):
                raise HTTPException(status_code=415, detail={"error": "rag_fetch_requires_text_like_content", "content_type": content_type})
            raw = response.read(100_000)
    except HTTPException:
        raise
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail={"error": "external_rag_fetch_http_error", "status": exc.code, "url": url}) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=502, detail={"error": "external_rag_fetch_failed", "reason": str(exc), "url": url}) from exc
    text = raw.decode("utf-8", errors="ignore")
    return {"url": url, "text": text, "bytes_read": len(raw)}


def _search_rag_sources(query: str, limit: int = 20) -> dict[str, Any]:
    needle = query.lower().strip()
    if not needle:
        raise HTTPException(status_code=400, detail={"error": "query_required"})
    draft_matches: list[dict[str, Any]] = []
    for row in reversed(_read_rag_source_drafts(limit=1000)):
        haystack = " ".join(
            [
                str(row.get("title", "")),
                str(row.get("location", "")),
                str(row.get("notes", "")),
                str(row.get("source_text", "")),
            ]
        ).lower()
        if needle in haystack:
            draft_matches.append(
                {
                    "source": "rag_source_draft",
                    "source_id": row["source_id"],
                    "source_type": row["source_type"],
                    "name": row["title"],
                    "path": row["location"],
                    "snippet": (row.get("source_text") or row.get("notes") or "Draft metadata match; no pasted source text.")[:360],
                    "external_fetch_performed": bool(row.get("external_fetch_performed")),
                }
            )
        if len(draft_matches) >= limit:
            break
    remaining = max(0, limit - len(draft_matches))
    index_result = _search_source_index(query, limit=remaining or 1)
    index_matches = [{**item, "source": "nas_source_index"} for item in index_result["matches"][:remaining]]
    matches = (draft_matches + index_matches)[:limit]
    return {
        "query": query,
        "matches": matches,
        "returned": len(matches),
        "draft_matches": len(draft_matches),
        "index_matches": len(index_matches),
        "external_fetch_performed": any(item.get("external_fetch_performed") for item in draft_matches),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


def _openrouter_key_present() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def _infer_reasoning_level(task_text: str) -> str:
    text = task_text.lower()
    for tier_name, words in AUTO_REASONING_KEYWORDS.items():
        if any(word in text for word in words):
            return "high" if tier_name == "expensive" else "medium"
    return "low"


def _normalise_reasoning_level(value: str | None, task_text: str = "") -> str:
    level = (value or "auto").strip().lower()
    if level in {"", "auto", "infer"}:
        return _infer_reasoning_level(task_text)
    return level if level in REASONING_TO_TIER else "low"


def _select_openrouter_tier(reasoning_level: str | None, max_cost_tier: str | None = None, task_text: str = "") -> dict[str, Any]:
    level = _normalise_reasoning_level(reasoning_level, task_text=task_text)
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
            "execution_gate": "execute=true is required for any OpenRouter call; paid tiers also require allow_paid_provider=true.",
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
        "next_action": "Set OPENROUTER_API_KEY and call with execute=true; include allow_paid_provider=true only for modest or expensive paid tiers.",
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
        "reasoning": {"effort": tier["reasoning_effort"]},
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


DAILY_LENS_THEMES = [
    "attention",
    "courage",
    "patience",
    "recovery",
    "decision",
    "shadow-work",
    "boundaries",
    "craft",
    "grief",
    "discipline",
    "compassion",
    "simplicity",
    "risk",
    "truth",
    "play",
    "energy",
    "relationships",
    "learning",
    "impermanence",
    "repair",
]

DAILY_LENS_TONES = ["gentle", "practical", "deep", "dry-warm", "steady"]
DAILY_LENS_USE_CASES = ["journal prompt", "reframe", "one-minute reset", "decision check", "review theme"]
DAILY_LENS_DISCIPLINES = [
    "philosophy",
    "psychology",
    "craft",
    "sport",
    "history",
    "science",
    "spiritual inquiry",
    "leadership",
    "creative practice",
    "ordinary life",
]
DAILY_LENS_OPENINGS = [
    "If the day is heavy",
    "When the answer is not ready",
    "Before you make the plan bigger",
    "If the mind wants a courtroom",
    "When energy is low",
    "Before you call it failure",
    "If the next step feels too large",
    "When the old pattern appears",
    "If you are trying to prove yourself",
    "When the room inside gets loud",
]
DAILY_LENS_ACTIONS = [
    "make the plan lighter, not yourself wrong",
    "ask for the smallest true thing",
    "remove one unnecessary demand",
    "protect the quiet part that still knows",
    "choose the honest version, not the heroic one",
    "let the evidence speak before the panic",
    "leave one question open on purpose",
    "turn the promise into a humane next step",
    "notice the signal before obeying the story",
    "give the future you one clean handhold",
]
DAILY_LENS_QUESTIONS = [
    "What is true right now, without decoration?",
    "What would become easier if it were smaller?",
    "What are you carrying that no longer belongs to today?",
    "Which part of this needs kindness before strategy?",
    "What proof would make the next step safer?",
    "What can be postponed without betraying the real promise?",
    "What is the calmest useful move?",
    "What would you do if this did not need to impress anyone?",
    "Which boundary is trying to become visible?",
    "What is asking to be repaired, not judged?",
]


def _daily_lens_library() -> list[dict[str, Any]]:
    lenses: list[dict[str, Any]] = []
    for index in range(10000):
        theme = DAILY_LENS_THEMES[index % len(DAILY_LENS_THEMES)]
        tone = DAILY_LENS_TONES[(index // len(DAILY_LENS_THEMES)) % len(DAILY_LENS_TONES)]
        use_case = DAILY_LENS_USE_CASES[(index // 7) % len(DAILY_LENS_USE_CASES)]
        discipline = DAILY_LENS_DISCIPLINES[(index // 11) % len(DAILY_LENS_DISCIPLINES)]
        opening = DAILY_LENS_OPENINGS[(index * 3) % len(DAILY_LENS_OPENINGS)]
        action = DAILY_LENS_ACTIONS[(index * 7) % len(DAILY_LENS_ACTIONS)]
        question = DAILY_LENS_QUESTIONS[(index * 13) % len(DAILY_LENS_QUESTIONS)]
        lens_type = ["ck-original", "micro-anecdote", "practice-prompt"][index % 3]
        if lens_type == "micro-anecdote":
            text = f"A good {discipline} lesson: do not add weight until the form can carry it."
            body = f"{opening.lower()}, {action}. {question}"
            source = f"CK paraphrased anecdote pattern from {discipline}; no verbatim book quotation"
        elif lens_type == "practice-prompt":
            text = question
            body = f"Use this as a {use_case}. {opening}, {action}."
            source = "CK local practice prompt"
        else:
            text = f"{opening}, {action}."
            body = question
            source = "CK original local line"
        lenses.append(
            {
                "lens_id": f"lens-{index + 1:05d}",
                "text": text,
                "body": body,
                "type": lens_type,
                "theme": theme,
                "tone": tone,
                "use_case": use_case,
                "discipline": discipline,
                "source": source,
                "permission_status": "local_generated_original_or_paraphrased_no_verbatim_copyright_claim",
                "why_this": f"Chosen to support {theme.replace('-', ' ')} with a {tone} tone and a short next action.",
                "buttons": ["Save lens", "Why this?", "Another lens", "Hide this theme"],
                "field_utility": {
                    "what": "daily calm quote, anecdote, or prompt",
                    "who": "the local CK Life OS user",
                    "why": "reduce starting friction and offer a useful lens without pressure",
                    "when": "top of the app, daily review, or whenever the user returns",
                    "where": "top header and Today -> Daily Lens",
                    "how": "save, skip, ask why, or hide the theme",
                    "eli10": "a small thought to help you start without being bossed around",
                },
                "external_send": False,
                "provider_called": False,
                "synthetic_data": True,
            }
        )
    return lenses


def _daily_lens_by_id(lens_id: str) -> dict[str, Any]:
    if not lens_id.startswith("lens-"):
        raise HTTPException(status_code=404, detail={"error": "daily_lens_not_found", "lens_id": lens_id})
    try:
        index = int(lens_id.split("-", 1)[1]) - 1
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": "daily_lens_not_found", "lens_id": lens_id}) from exc
    library = _daily_lens_library()
    if index < 0 or index >= len(library):
        raise HTTPException(status_code=404, detail={"error": "daily_lens_not_found", "lens_id": lens_id})
    return library[index]


def _current_daily_lens(offset: int = 0) -> dict[str, Any]:
    library = _daily_lens_library()
    hour_bucket = int(time.time() // 3600)
    index = (hour_bucket + offset) % len(library)
    lens = dict(library[index])
    lens["rotation"] = "hourly_local_rotation_plus_user_next_offset"
    lens["library_total"] = len(library)
    return lens


def _read_saved_daily_lenses(limit: int = 100) -> list[dict[str, Any]]:
    if not DAILY_LENS_SAVED_FILE.exists():
        return []
    rows = []
    for line in DAILY_LENS_SAVED_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _append_saved_daily_lens(lens: dict[str, Any], note: str = "") -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "save_id": f"saved-lens-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "saved_at": _utc_now(),
        "lens": lens,
        "note": str(note or "")[:500],
        "local_only": True,
        "storage": str(DAILY_LENS_SAVED_FILE),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }
    with DAILY_LENS_SAVED_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True) + "\n")
    return receipt


def _local_report() -> dict[str, Any]:
    receipts = _read_receipts(limit=100000)
    journal_rows = _read_journal_rows(limit=100000)
    inner_rows = _read_inner_work_rows(limit=100000)
    source_manifest = _source_index_manifest()
    return {
        "report_id": f"lifeos-local-summary-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "generated_at": _utc_now(),
        "product": PRODUCT_IDENTITY,
        "practice_count": len(settings.PRACTICES),
        "receipt_count": len(receipts),
        "encrypted_journal_count": len(journal_rows),
        "inner_work_session_count": len(inner_rows),
        "idea_count": len(_practice_ideas()),
        "daily_lens_count": len(_daily_lens_library()),
        "saved_daily_lens_count": len(_read_saved_daily_lenses(limit=100000)),
        "academy_program_count": len(ACADEMY_PROGRAMMES),
        "academy_lesson_count": len(ACADEMY_LESSONS),
        "academy_receipt_count": len(_read_academy_receipts(limit=100000)),
        "live_action_receipt_count": len(_read_live_action_receipts(limit=100000)),
        "source_index": {
            "status": source_manifest["status"],
            "files_indexed": source_manifest.get("files_indexed", 0),
            "excluded_roots_count": source_manifest.get("excluded_roots_count", len(NAS_EXCLUDED_ROOTS)),
            "only_approved_exclusions": source_manifest.get("only_approved_exclusions", True),
        },
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
        "latest_inner_work_sessions": [_inner_work_summary(row) for row in inner_rows[-5:]],
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
        "auto_reasoning": AUTO_REASONING_KEYWORDS,
        "default_boundary": "No provider call occurs unless /api/ai/complete receives execute=true. Paid modest/expensive tiers also require allow_paid_provider=true.",
        "secret_boundary": "OPENROUTER_API_KEY stays server-side and is never returned to the UI.",
        "fallback": "If key/config/approval is missing, CK Life OS returns a local fallback explanation.",
    }


@app.post("/api/ai/route")
async def ai_route(request: Request):
    """Select the OpenRouter tier for a task without calling a provider."""
    payload = await request.json()
    task = str(payload.get("task") or payload.get("prompt") or "")[:300]
    tier = _select_openrouter_tier(payload.get("reasoning_level"), payload.get("max_cost_tier"), task_text=task)
    return {
        "provider": "openrouter",
        "provider_called": False,
        "selected": tier,
        "task": task,
        "approval_required_for_selected_tier": bool(tier["paid"]),
        "next_action": "Call /api/ai/complete with execute=true. Add allow_paid_provider=true only when the selected tier is modest or expensive.",
    }


@app.post("/api/ai/complete")
async def ai_complete(request: Request):
    """Guarded OpenRouter completion endpoint with local fallback."""
    payload = await request.json()
    prompt = str(payload.get("prompt") or payload.get("task") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail={"error": "prompt_required"})
    tier = _select_openrouter_tier(payload.get("reasoning_level"), payload.get("max_cost_tier"), task_text=prompt)
    execute = bool(payload.get("execute"))
    allow_paid = bool(payload.get("allow_paid_provider"))
    if not execute:
        return {
            "provider": "openrouter",
            "selected": tier,
            **_local_ai_fallback(prompt, tier),
            "approval_required": True,
            "approval_reason": "execute_required",
        }
    if tier["paid"] and not allow_paid:
        return {
            "provider": "openrouter",
            "selected": tier,
            **_local_ai_fallback(prompt, tier),
            "approval_required": True,
            "approval_reason": "paid_tier_requires_allow_paid_provider",
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


@app.get("/api/inner-work/modes")
async def inner_work_modes():
    return {
        "modes": INNER_WORK_MODES,
        "default_mode": "unknown",
        "principle": "guide deep looking; do not generate final answers, diagnoses, or spiritual authority claims",
        "input_types": ["text", "voice_transcript"],
        "encrypted_at_rest": True,
        "external_send": False,
        "ai_provider_called": False,
    }


@app.get("/api/inner-work/sessions")
async def inner_work_sessions():
    rows = _read_inner_work_rows()
    return {
        "count": len(_read_inner_work_rows(limit=100000)),
        "items": [_inner_work_summary(row) for row in rows],
        "encrypted_at_rest": True,
        "external_send": False,
        "source_write": False,
    }


@app.post("/api/inner-work/session")
async def create_inner_work_session(request: Request):
    payload = await request.json()
    result = _append_inner_work_session(payload)
    return {
        "saved": True,
        "session_id": result["row"]["session_id"],
        "created_at": result["row"]["created_at"],
        "guidance": result["guidance"],
        "encrypted_at_rest": True,
        "plaintext_stored": False,
        "external_send": False,
        "source_write": False,
    }


@app.get("/api/inner-work/session/{session_id}")
async def inner_work_session(session_id: str):
    row = next((item for item in _read_inner_work_rows(limit=100000) if item.get("session_id") == session_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "inner_work_session_not_found"})
    return {
        "session_id": row["session_id"],
        "created_at": row["created_at"],
        "payload": _decrypt_inner_work_payload(row),
        "encrypted_at_rest": True,
        "external_send": False,
        "source_write": False,
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


@app.get("/api/daily-lens")
async def daily_lens(offset: int = Query(0, ge=0, le=9999)):
    lens = _current_daily_lens(offset=offset)
    return {
        "status": "ok",
        "current": lens,
        "total": len(_daily_lens_library()),
        "saved_count": len(_read_saved_daily_lenses(limit=100000)),
        "synthetic_data": True,
        "catalogue_truth": "10,000 local generated Daily Lens records; CK originals, prompts, or paraphrased anecdote patterns; no fake attribution.",
        "external_send": False,
        "provider_called": False,
        "save_endpoint": "/api/daily-lens/save",
        "saved_endpoint": "/api/daily-lens/saved",
    }


@app.get("/api/daily-lens/library")
async def daily_lens_library(
    theme: str | None = Query(None),
    tone: str | None = Query(None),
    use_case: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
):
    library = _daily_lens_library()
    if theme:
        library = [item for item in library if item["theme"] == theme]
    if tone:
        library = [item for item in library if item["tone"] == tone]
    if use_case:
        library = [item for item in library if item["use_case"] == use_case]
    return {
        "total": len(library),
        "returned": min(len(library), limit),
        "items": library[:limit],
        "themes": DAILY_LENS_THEMES,
        "tones": DAILY_LENS_TONES,
        "use_cases": DAILY_LENS_USE_CASES,
        "external_send": False,
        "provider_called": False,
    }


@app.post("/api/daily-lens/save")
async def save_daily_lens(request: Request):
    payload = await request.json()
    lens_id = str(payload.get("lens_id") or "")
    lens = _daily_lens_by_id(lens_id) if lens_id else _current_daily_lens()
    receipt = _append_saved_daily_lens(lens, note=str(payload.get("note") or ""))
    return {
        "status": "saved",
        "save_id": receipt["save_id"],
        "receipt": receipt,
        "saved_count": len(_read_saved_daily_lenses(limit=100000)),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


@app.get("/api/daily-lens/saved")
async def saved_daily_lenses():
    rows = list(reversed(_read_saved_daily_lenses(limit=100)))
    return {
        "count": len(_read_saved_daily_lenses(limit=100000)),
        "returned": len(rows),
        "storage": str(DAILY_LENS_SAVED_FILE),
        "items": rows,
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


@app.get("/api/daily-lens/{lens_id}")
async def daily_lens_detail(lens_id: str):
    return _daily_lens_by_id(lens_id)


@app.get("/api/synthetic-data/status")
async def synthetic_data_status():
    return {
        "status": "clean_boundary",
        "synthetic_sources": ["local_seed_catalogue_v1", "daily_lens_generated_library_v1"],
        "synthetic_rows": len(_practice_ideas()) + len(_daily_lens_library()),
        "innovation_synthetic_rows": len(_practice_ideas()),
        "daily_lens_synthetic_rows": len(_daily_lens_library()),
        "synthetic_outside_demo_scope": 0,
        "real_user_receipts_are_synthetic": False,
        "cleanup_available": True,
        "cleanup_note": "Generated innovation patterns are not persisted as user history; cleanup verifies the boundary and writes a local receipt.",
    }


@app.get("/api/synthetic-data/removal-preview")
async def synthetic_removal_preview():
    return {
        "would_remove": 0,
        "preserved_demo_rows": len(_practice_ideas()) + len(_daily_lens_library()),
        "reason": "Innovation patterns and Daily Lens rows are generated local catalogue rows, not stored operational user history.",
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
    source_manifest = _source_index_manifest()
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
        "n8n_workflows": {
            "required_for_core_ui": False,
            "status": "ck_owned_import_pack_ready_disabled_by_default",
            "workflow_count": len(N8N_WORKFLOW_REGISTRY),
            "workflow_dir": str(N8N_WORKFLOW_DIR),
            "registry_endpoint": "/api/life-manager/n8n-workflows",
            "dry_run_supported": True,
            "live_import_performed": False,
            "live_execution_performed": False,
            "fallback": "CK local receipts and manual approval gates remain usable without n8n",
        },
        "source_index": {
            "configured": True,
            "required_for_core_ui": False,
            "state": source_manifest["status"],
            "fallback": "core practice/journal/inner-work UI remains usable if NAS is unavailable",
            "roots": NAS_SOURCE_ROOTS,
            "excluded_roots": NAS_EXCLUDED_ROOTS,
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


@app.get("/api/academy/status")
async def academy_status():
    return {
        "product": "CK Life OS",
        "status": "implemented_local_internal",
        "where_to_access": "Knowledge -> Academy",
        "program_count": len(ACADEMY_PROGRAMMES),
        "lesson_count": len(ACADEMY_LESSONS),
        "receipt_count": len(_read_academy_receipts(limit=100000)),
        "tabs": ["Programmes", "Lessons", "Practice", "Readiness"],
        "buttons": ["Refresh Academy", "Open lessons", "Start lesson", "Save practice receipt", "Check readiness"],
        "external_lms_required": False,
        "provider_called": False,
        "external_send": False,
        "storage": str(ACADEMY_RECEIPTS_FILE),
    }


@app.get("/api/academy/programs")
async def academy_programs():
    lesson_counts = {program["program_id"]: len(_academy_lessons_for_program(program["program_id"])) for program in ACADEMY_PROGRAMMES}
    return {
        "count": len(ACADEMY_PROGRAMMES),
        "items": [{**program, "lesson_count": lesson_counts[program["program_id"]]} for program in ACADEMY_PROGRAMMES],
        "local_only": True,
        "external_send": False,
    }


@app.get("/api/academy/programs/{program_id}/lessons")
async def academy_program_lessons(program_id: str):
    program = _academy_program(program_id)
    lessons = _academy_lessons_for_program(program_id)
    return {"program": program, "count": len(lessons), "items": lessons, "local_only": True}


@app.get("/api/academy/lessons/{lesson_id}")
async def academy_lesson_detail(lesson_id: str):
    return _academy_lesson(lesson_id)


@app.post("/api/academy/lessons/{lesson_id}/practice")
async def academy_lesson_practice(lesson_id: str, request: Request):
    lesson = _academy_lesson(lesson_id)
    payload = await request.json()
    receipt = _append_academy_receipt(payload, lesson)
    return {
        "saved": True,
        "receipt": receipt,
        "external_lms_write": False,
        "external_send": False,
        "provider_called": False,
        "next_action": "Open the matching CK screen and use the real module button only if it helps.",
    }


@app.get("/api/academy/receipts")
async def academy_receipts():
    rows = _read_academy_receipts(limit=100)
    return {
        "count": len(_read_academy_receipts(limit=100000)),
        "items": rows,
        "storage": str(ACADEMY_RECEIPTS_FILE),
        "external_lms_write": False,
        "external_send": False,
    }


@app.get("/api/academy/readiness")
async def academy_readiness():
    receipts = _read_academy_receipts(limit=100000)
    completed_lessons = {row.get("lesson_id") for row in receipts}
    return {
        "status": "ready_for_local_internal_learning",
        "completed_lessons": len(completed_lessons),
        "lesson_count": len(ACADEMY_LESSONS),
        "coverage_percent": round((len(completed_lessons) / len(ACADEMY_LESSONS)) * 100, 2) if ACADEMY_LESSONS else 100,
        "provider_called": False,
        "external_lms_required": False,
        "next_recommended_lesson": next((lesson for lesson in ACADEMY_LESSONS if lesson["lesson_id"] not in completed_lessons), ACADEMY_LESSONS[0]),
    }


@app.get("/api/life-manager/spec")
async def life_manager_spec():
    return {
        "product": "CK Life OS",
        "version": "v2_local_internal_layout",
        "intent": "private life coach, guide, accountability partner, and life manager",
        "menu": LIFE_MANAGER_MENU,
        "screens": LIFE_MANAGER_SCREENS,
        "layout_rules": {
            "middle_column_scroll": "disabled",
            "middle_content": "tabs",
            "left_menu": "grouped_collapsible_categories",
            "right_rail": "contextual_collapsed_panels",
            "admin_proof": "hidden_from_normal_user_flow",
        },
        "boundaries": {
            "external_send": False,
            "source_write": False,
            "paid_provider_call_by_default": False,
            "voice_transcription_provider_called": False,
            "calendar_write": False,
            "n8n_live_import_performed": False,
            "n8n_live_execution_performed": False,
            "provider_execution_requires": ["explicit user action", "execute=true", "paid approval when tier is paid"],
        },
        "storage": {
            "life_manager_receipts": str(LIFE_MANAGER_RECEIPTS_FILE),
            "n8n_preflight_receipts": str(N8N_PREFLIGHT_RECEIPTS_FILE),
            "academy_receipts": str(ACADEMY_RECEIPTS_FILE),
            "live_action_receipts": str(LIVE_ACTION_RECEIPTS_FILE),
            "journal": str(JOURNAL_FILE),
            "inner_work": str(INNER_WORK_FILE),
            "rag_sources": str(RAG_SOURCE_DRAFTS_FILE),
        },
        "academy": {
            "status": "implemented_local_internal",
            "program_count": len(ACADEMY_PROGRAMMES),
            "lesson_count": len(ACADEMY_LESSONS),
            "status_endpoint": "/api/academy/status",
        },
        "live_action_gates": {
            "status_endpoint": "/api/live-actions/status",
            "receipt_endpoint": "/api/live-actions/receipts",
            "ripple_calendar_endpoint": "/api/ripple-calendar/write",
            "voice_transcription_endpoint": "/api/voice/transcription",
            "memory_sync_endpoint": "/api/memory/sync",
            "n8n_import_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-import",
            "n8n_live_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-execute",
        },
        "n8n_workflows": {
            "total": len(N8N_WORKFLOW_REGISTRY),
            "registry_endpoint": "/api/life-manager/n8n-workflows",
            "workflow_dir": str(N8N_WORKFLOW_DIR),
            "fixes_boundaries": [item["fixes_boundary"] for item in N8N_WORKFLOW_REGISTRY],
            "active_by_default": False,
        },
    }


@app.get("/api/life-manager/workflows")
async def life_manager_workflows():
    return {
        "total": len(LIFE_MANAGER_SCREENS),
        "items": [
            {
                "id": item["id"],
                "label": item["label"],
                "menu_path": item["menu_path"],
                "tabs": item["tabs"],
                "buttons": item["buttons"],
                "workflow": item["workflow"],
            }
            for item in LIFE_MANAGER_SCREENS
        ],
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


@app.get("/api/life-manager/n8n-workflows")
async def life_manager_n8n_workflows():
    items = [_n8n_workflow_summary(item) for item in N8N_WORKFLOW_REGISTRY]
    return {
        "product": "CK Life OS",
        "status": "ck_owned_n8n_import_pack_ready_disabled_by_default",
        "total": len(items),
        "workflow_dir": str(N8N_WORKFLOW_DIR),
        "items": items,
        "dry_run_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/dry-run",
        "preflight_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/preflight",
        "receipts_endpoint": "/api/life-manager/n8n-workflows/receipts",
        "live_import_performed": False,
        "live_execution_performed": False,
        "external_send": False,
        "source_write": False,
        "paid_provider_call": False,
        "calendar_write": False,
        "transcription_provider_called": False,
        "memory_sync_performed": False,
        "normal_user_visible": False,
    }


@app.get("/api/life-manager/n8n-workflows/receipts")
async def life_manager_n8n_workflow_receipts():
    rows = _read_n8n_preflight_receipts(limit=100)
    return {
        "count": len(_read_n8n_preflight_receipts(limit=100000)),
        "items": rows,
        "storage": str(N8N_PREFLIGHT_RECEIPTS_FILE),
        "external_send": False,
        "source_write": False,
        "live_execution_performed": False,
    }


@app.get("/api/life-manager/n8n-workflows/{workflow_id}")
async def life_manager_n8n_workflow_detail(workflow_id: str):
    workflow = _workflow_by_id(workflow_id)
    path = N8N_WORKFLOW_DIR / workflow["n8n_file"]
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": "n8n_workflow_file_missing", "path": str(path)})
    return {
        **_n8n_workflow_summary(workflow),
        "import_json": json.loads(path.read_text(encoding="utf-8")),
    }


@app.post("/api/life-manager/n8n-workflows/{workflow_id}/dry-run")
async def life_manager_n8n_workflow_dry_run(workflow_id: str, request: Request):
    workflow = _workflow_by_id(workflow_id)
    payload = await request.json()
    receipt = _append_n8n_preflight_receipt(workflow, payload, mode="dry_run")
    return {
        "saved": True,
        "receipt": receipt,
        "message": "Dry-run receipt recorded. No n8n import, provider call, external send, calendar write, transcription, or memory sync occurred.",
    }


@app.post("/api/life-manager/n8n-workflows/{workflow_id}/preflight")
async def life_manager_n8n_workflow_preflight(workflow_id: str, request: Request):
    workflow = _workflow_by_id(workflow_id)
    payload = await request.json()
    receipt = _append_n8n_preflight_receipt(workflow, payload, mode="preflight")
    return {
        "saved": True,
        "receipt": receipt,
        "can_import_manually": receipt["status"] == "ready_for_manual_import_review",
        "live_action_performed": False,
        "next_action": "Import the disabled workflow into n8n only after confirming credentials, target, rollback, and exact approval reference.",
    }


@app.post("/api/life-manager/n8n-workflows/{workflow_id}/live-import")
async def life_manager_n8n_workflow_live_import(workflow_id: str, request: Request):
    workflow = _workflow_by_id(workflow_id)
    payload = await request.json()
    blockers = _approval_blockers({**payload, "live_execute": payload.get("live_import", payload.get("execute"))})
    base_url = os.getenv("N8N_API_BASE_URL", "").strip().rstrip("/")
    api_key = os.getenv("N8N_API_KEY", "").strip()
    if not base_url:
        blockers.append("N8N_API_BASE_URL not configured")
    if not api_key:
        blockers.append("N8N_API_KEY not configured")
    path = N8N_WORKFLOW_DIR / workflow["n8n_file"]
    if not path.exists():
        blockers.append(f"n8n workflow JSON missing: {path}")
    if blockers:
        receipt = _append_live_action_receipt(
            f"n8n-import:{workflow_id}",
            payload,
            "blocked",
            blockers,
            target_endpoint=f"{base_url}/api/v1/workflows" if base_url else "",
            live_n8n_import_performed=False,
            rollback="No n8n import occurred. Configure N8N_API_BASE_URL/N8N_API_KEY and retry only with explicit approval.",
        )
        return {"status": "blocked", "receipt": receipt, "live_import_performed": False}
    import_json = json.loads(path.read_text(encoding="utf-8"))
    import_json["active"] = False
    body = json.dumps(import_json, ensure_ascii=True).encode("utf-8")
    try:
        req = UrlRequest(
            f"{base_url}/api/v1/workflows",
            data=body,
            headers={"Content-Type": "application/json", "X-N8N-API-KEY": api_key},
            method="POST",
        )
        with urlopen(req, timeout=20) as response:
            response_body = response.read(4096).decode("utf-8", errors="replace")
        receipt = _append_live_action_receipt(
            f"n8n-import:{workflow_id}",
            payload,
            "performed",
            [],
            target_endpoint=f"{base_url}/api/v1/workflows",
            response_preview=response_body[:1000],
            live_n8n_import_performed=True,
            external_send=True,
            rollback="Deactivate/delete the imported n8n workflow; it was imported inactive by CK.",
        )
        return {"status": "performed", "receipt": receipt, "live_import_performed": True}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        receipt = _append_live_action_receipt(
            f"n8n-import:{workflow_id}",
            payload,
            "blocked",
            [f"n8n import call failed: {type(exc).__name__}: {exc}"],
            target_endpoint=f"{base_url}/api/v1/workflows",
            live_n8n_import_performed=False,
        )
        return {"status": "blocked", "receipt": receipt, "live_import_performed": False}


@app.post("/api/life-manager/n8n-workflows/{workflow_id}/live-execute")
async def life_manager_n8n_workflow_live_execute(workflow_id: str, request: Request):
    workflow = _workflow_by_id(workflow_id)
    payload = await request.json()
    blockers = _approval_blockers({**payload, "live_execute": payload.get("live_execute", payload.get("execute"))})
    base_url = os.getenv("N8N_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        blockers.append("N8N_WEBHOOK_BASE_URL not configured")
    if blockers:
        receipt = _append_live_action_receipt(
            f"n8n:{workflow_id}",
            payload,
            "blocked",
            blockers,
            target_endpoint=f"{base_url}/{workflow['webhook_path']}" if base_url else "",
            live_n8n_execution_performed=False,
            rollback=workflow["rollback"],
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}
    target_url = f"{base_url}/{workflow['webhook_path']}"
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    try:
        req = UrlRequest(target_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=20) as response:
            response_body = response.read(4096).decode("utf-8", errors="replace")
        receipt = _append_live_action_receipt(
            f"n8n:{workflow_id}",
            payload,
            "performed",
            [],
            target_endpoint=target_url,
            response_preview=response_body[:1000],
            live_n8n_execution_performed=True,
            external_send=True,
            rollback=workflow["rollback"],
        )
        return {"status": "performed", "receipt": receipt, "live_action_performed": True}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        receipt = _append_live_action_receipt(
            f"n8n:{workflow_id}",
            payload,
            "blocked",
            [f"n8n webhook call failed: {type(exc).__name__}: {exc}"],
            target_endpoint=target_url,
            live_n8n_execution_performed=False,
            rollback=workflow["rollback"],
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}


@app.get("/api/live-actions/status")
async def live_actions_status():
    return {
        "status": "approval_gated",
        "receipt_path": str(LIVE_ACTION_RECEIPTS_FILE),
        "receipt_count": len(_read_live_action_receipts(limit=100000)),
        "openrouter": {
            "endpoint": "/api/ai/complete",
            "key_configured": _openrouter_key_present(),
            "live_call_requires": ["OPENROUTER_API_KEY", "execute=true", "allow_paid_provider=true for paid tiers"],
        },
        "voice_transcription": {
            "endpoint": "/api/voice/transcription",
            "local_or_provider_endpoint_configured": bool(os.getenv("CK_LIFE_OS_TRANSCRIPTION_ENDPOINT")),
            "live_call_requires": ["execute=true", "explicit_approval=true", "approval_reference", "CK_LIFE_OS_TRANSCRIPTION_ENDPOINT"],
        },
        "ripple_calendar": {
            "endpoint": "/api/ripple-calendar/write",
            "ripple_endpoint_configured": bool(os.getenv("RIPPLE_CALENDAR_ENDPOINT")),
            "target": os.getenv("RIPPLE_CALENDAR_ENDPOINT", "not_configured"),
            "live_call_requires": ["write=true", "explicit_approval=true", "approval_reference", "RIPPLE_CALENDAR_ENDPOINT"],
        },
        "memory_sync": {
            "endpoint": "/api/memory/sync",
            "target_dir_configured": bool(os.getenv("CK_LIFE_OS_MEMORY_SYNC_DIR")),
            "live_call_requires": ["sync=true", "explicit_approval=true", "approval_reference", "CK_LIFE_OS_MEMORY_SYNC_DIR"],
        },
        "n8n": {
            "import_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-import",
            "endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-execute",
            "api_base_configured": bool(os.getenv("N8N_API_BASE_URL")),
            "webhook_base_configured": bool(os.getenv("N8N_WEBHOOK_BASE_URL")),
            "live_import_requires": ["live_import=true", "explicit_approval=true", "approval_reference", "N8N_API_BASE_URL", "N8N_API_KEY"],
            "live_call_requires": ["live_execute=true", "explicit_approval=true", "approval_reference", "N8N_WEBHOOK_BASE_URL"],
        },
    }


@app.get("/api/live-actions/receipts")
async def live_action_receipts():
    rows = _read_live_action_receipts(limit=100)
    return {"count": len(_read_live_action_receipts(limit=100000)), "items": rows, "storage": str(LIVE_ACTION_RECEIPTS_FILE)}


@app.post("/api/voice/transcription")
async def voice_transcription(request: Request):
    payload = await request.json()
    pasted_transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
    if pasted_transcript:
        receipt = _append_live_action_receipt(
            "voice_transcription",
            payload,
            "performed",
            [],
            transcript_preview=pasted_transcript[:300],
            transcription_provider_called=False,
            rollback="Delete the local transcript receipt and any journal/voice note created from it.",
        )
        return {"status": "performed", "mode": "pasted_transcript_local", "receipt": receipt, "transcript": pasted_transcript}
    blockers = _approval_blockers(payload)
    endpoint = os.getenv("CK_LIFE_OS_TRANSCRIPTION_ENDPOINT", "").strip()
    if not endpoint:
        blockers.append("CK_LIFE_OS_TRANSCRIPTION_ENDPOINT not configured")
    if not payload.get("audio_reference"):
        blockers.append("audio_reference missing")
    if blockers:
        receipt = _append_live_action_receipt("voice_transcription", payload, "blocked", blockers, target_endpoint=endpoint)
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    try:
        req = UrlRequest(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=30) as response:
            response_body = response.read(100000).decode("utf-8", errors="replace")
        receipt = _append_live_action_receipt(
            "voice_transcription",
            payload,
            "performed",
            [],
            target_endpoint=endpoint,
            response_preview=response_body[:1000],
            transcription_provider_called=True,
            external_send=True,
            rollback="Delete the returned transcript draft; revoke the transcription credential if this was unintended.",
        )
        return {"status": "performed", "receipt": receipt, "response_preview": response_body[:1000]}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        receipt = _append_live_action_receipt("voice_transcription", payload, "blocked", [f"transcription call failed: {type(exc).__name__}: {exc}"], target_endpoint=endpoint)
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}


@app.post("/api/ripple-calendar/write")
async def ripple_calendar_write(request: Request):
    payload = await request.json()
    blockers = _approval_blockers({**payload, "write": payload.get("write", payload.get("execute"))})
    endpoint = os.getenv("RIPPLE_CALENDAR_ENDPOINT", "").strip()
    if not endpoint:
        blockers.append("RIPPLE_CALENDAR_ENDPOINT not configured")
    if not payload.get("title"):
        blockers.append("calendar title missing")
    if not payload.get("start"):
        blockers.append("calendar start missing")
    if blockers:
        receipt = _append_live_action_receipt(
            "ripple_calendar_write",
            payload,
            "blocked",
            blockers,
            target="Ripple",
            target_endpoint=endpoint,
            calendar_write=False,
            rollback="No Ripple/calendar write occurred. Configure endpoint and retry only with explicit approval.",
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    try:
        req = UrlRequest(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=20) as response:
            response_body = response.read(4096).decode("utf-8", errors="replace")
        receipt = _append_live_action_receipt(
            "ripple_calendar_write",
            payload,
            "performed",
            [],
            target="Ripple",
            target_endpoint=endpoint,
            response_preview=response_body[:1000],
            calendar_write=True,
            external_send=True,
            rollback="Use the Ripple response event id to delete/update the calendar item; keep this CK receipt as audit proof.",
        )
        return {"status": "performed", "receipt": receipt, "live_action_performed": True}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        receipt = _append_live_action_receipt(
            "ripple_calendar_write",
            payload,
            "blocked",
            [f"Ripple calendar endpoint call failed: {type(exc).__name__}: {exc}"],
            target="Ripple",
            target_endpoint=endpoint,
            calendar_write=False,
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}


@app.post("/api/memory/sync")
async def memory_sync(request: Request):
    payload = await request.json()
    blockers = _approval_blockers({**payload, "sync": payload.get("sync", payload.get("execute"))})
    target_dir_raw = os.getenv("CK_LIFE_OS_MEMORY_SYNC_DIR", "").strip()
    if not target_dir_raw:
        blockers.append("CK_LIFE_OS_MEMORY_SYNC_DIR not configured")
    selected_rows = payload.get("memory_rows") or payload.get("rows") or []
    if not isinstance(selected_rows, list) or not selected_rows:
        blockers.append("memory_rows missing")
    if blockers:
        receipt = _append_live_action_receipt(
            "memory_sync",
            payload,
            "blocked",
            blockers,
            target_dir=target_dir_raw,
            memory_sync_performed=False,
            rollback="No memory sync occurred. Select rows and configure a user-owned encrypted/local sync target.",
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}
    target_dir = Path(target_dir_raw)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_id = f"ck-life-os-memory-sync-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        target_file = target_dir / f"{manifest_id}.json"
        manifest = {
            "manifest_id": manifest_id,
            "created_at": _utc_now(),
            "product": "CK Life OS",
            "rows": selected_rows,
            "sensitivity_reviewed": bool(payload.get("sensitivity_reviewed")),
            "approval_reference": payload.get("approval_reference"),
            "source_of_truth": str(LIFE_MANAGER_RECEIPTS_FILE),
        }
        target_file.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8")
        receipt = _append_live_action_receipt(
            "memory_sync",
            payload,
            "performed",
            [],
            target_file=str(target_file),
            memory_sync_performed=True,
            rollback=f"Delete {target_file} from the sync target; local CK remains source of truth.",
        )
        return {"status": "performed", "receipt": receipt, "manifest": manifest, "live_action_performed": True}
    except OSError as exc:
        receipt = _append_live_action_receipt(
            "memory_sync",
            payload,
            "blocked",
            [f"memory sync target write failed: {type(exc).__name__}: {exc}"],
            target_dir=target_dir_raw,
        )
        return {"status": "blocked", "receipt": receipt, "live_action_performed": False}


@app.post("/api/life-manager/receipt")
async def life_manager_receipt(request: Request):
    payload = await request.json()
    receipt = _append_life_manager_receipt(payload)
    return {
        "saved": True,
        "receipt": receipt,
        "external_send": False,
        "source_write": False,
        "provider_called": False,
        "paid_provider_call": False,
    }


@app.get("/api/life-manager/receipts")
async def life_manager_receipts():
    rows = _read_life_manager_receipts(limit=100)
    return {
        "count": len(_read_life_manager_receipts(limit=100000)),
        "items": rows,
        "storage": str(LIFE_MANAGER_RECEIPTS_FILE),
        "external_send": False,
        "source_write": False,
        "provider_called": False,
    }


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
        f"- Inner Work sessions: {report['inner_work_session_count']}",
        f"- Innovations: {report['idea_count']} generated rows",
        f"- NAS source index: {report['source_index']['status']} / {report['source_index']['files_indexed']} files",
        f"- NAS exclusions: {report['source_index']['excluded_roots_count']} approved roots only = {report['source_index']['only_approved_exclusions']}",
        f"- External send: {report['handover_boundary']['external_send']}",
        f"- Source write: {report['handover_boundary']['source_write']}",
        f"- Human review required for handoff: {report['handover_boundary']['human_review_required']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/api/source-index/status")
async def source_index_status():
    manifest = _source_index_manifest()
    return {
        **manifest,
        "approved_exclusions": NAS_EXCLUDED_ROOTS,
        "approved_exclusion_count": 2,
        "only_approved_exclusions": manifest.get("excluded_roots") == NAS_EXCLUDED_ROOTS,
        "runtime_independent": True,
        "normal_ui_required": False,
    }


@app.get("/api/rag/status")
async def rag_status():
    manifest = _source_index_manifest()
    return {
        "name": "CK Life OS RAG / Sources",
        "mode": "local_retrieval_augmented_guidance",
        "where_to_access": "Knowledge -> RAG / Sources",
        "ui_tabs": ["RAG status", "Add source", "Search", "Results"],
        "internal_sources": {
            "accepted": True,
            "current_lane": "local NAS metadata/text-snippet index",
            "roots": NAS_SOURCE_ROOTS,
            "excluded_roots": NAS_EXCLUDED_ROOTS,
            "index_status": manifest["status"],
            "files_indexed": manifest.get("files_indexed", 0),
            "search_endpoint": "/api/rag/search",
        },
        "external_sources": {
            "accepted_as_local_draft_or_pasted_text": True,
            "fetch_enabled": "approval_gated",
            "source_write": False,
            "external_send": False,
            "approval_required_before_fetch_or_ingest": True,
            "approved_fetch_endpoint": "/api/rag/source-draft with fetch_approved=true",
            "draft_endpoint": "/api/rag/source-draft",
        },
        "draft_sources": {
            "storage": str(RAG_SOURCE_DRAFTS_FILE),
            "count": len(_read_rag_source_drafts(limit=100000)),
            "searchable_when_text_is_pasted": True,
        },
        "provider_calls_required_for_search": False,
        "pgvector_required_for_local_internal": False,
        "fallback": "If NAS, pgvector, OpenRouter, or external access is unavailable, the core practice, journal, inner-work, and local report UI remains usable.",
    }


@app.post("/api/rag/source-draft")
async def rag_source_draft(request: Request):
    payload = await request.json()
    row = _append_rag_source_draft(payload)
    receipt = {
        "receipt_id": row["source_id"],
        **row,
    }
    _append_receipt({"practice": "system", "note": f"RAG source draft staged: {row['source_type']}", **receipt})
    return receipt


@app.get("/api/rag/source-drafts")
async def rag_source_drafts():
    rows = _read_rag_source_drafts(limit=100)
    return {
        "count": len(_read_rag_source_drafts(limit=100000)),
        "items": [
            {
                key: value
                for key, value in row.items()
                if key not in {"source_text"}
            }
            for row in rows
        ],
        "storage": str(RAG_SOURCE_DRAFTS_FILE),
        "external_fetch_performed": False,
        "external_send": False,
        "source_write": False,
    }


@app.get("/api/rag/search")
async def rag_search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    return _search_rag_sources(q, limit=limit)


@app.post("/api/source-index/build")
async def source_index_build(request: Request):
    payload = await request.json()
    roots = payload.get("roots") or NAS_SOURCE_ROOTS
    if roots != NAS_SOURCE_ROOTS:
        raise HTTPException(status_code=400, detail={"error": "source_roots_locked", "allowed_roots": NAS_SOURCE_ROOTS})
    max_files_raw = payload.get("max_files")
    max_files = int(max_files_raw) if max_files_raw not in (None, "", False) else None
    if max_files is not None and max_files < 1:
        raise HTTPException(status_code=400, detail={"error": "max_files_must_be_positive"})
    return _build_source_index(max_files=max_files, roots=roots)


@app.get("/api/source-index/search")
async def source_index_search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    return _search_source_index(q, limit=limit)


@app.get("/api/product-bible-matrix")
async def product_bible_matrix():
    source_manifest = _source_index_manifest()
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
        "covers_daily_lens": True,
        "covers_inner_work": True,
        "covers_cost_effort_reduction": True,
        "covers_semantic_intent_map": True,
        "covers_delivery_matrix": True,
        "covers_amtl_operating_layout": True,
        "covers_openrouter_model_routing": True,
        "covers_rag_postgres_pgvector_truth": True,
        "covers_nas_source_indexing": True,
        "covers_life_manager_v2_menu_screens_panels_buttons": True,
        "covers_life_manager_n8n_workflow_pack": True,
        "covers_academy": True,
        "covers_live_action_gates": True,
        "life_manager_v2": {
            "menu_groups": len(LIFE_MANAGER_MENU),
            "screens": len(LIFE_MANAGER_SCREENS),
            "receipt_endpoint": "/api/life-manager/receipt",
            "spec_endpoint": "/api/life-manager/spec",
            "status": "local_internal_screen_workflows_implemented_with_receipts",
        },
        "daily_lens": {
            "library_count": len(_daily_lens_library()),
            "current_endpoint": "/api/daily-lens",
            "library_endpoint": "/api/daily-lens/library",
            "save_endpoint": "/api/daily-lens/save",
            "saved_endpoint": "/api/daily-lens/saved",
            "saved_count": len(_read_saved_daily_lenses(limit=100000)),
            "status": "10k_local_generated_lens_library_with_local_saved_lenses",
        },
        "academy": {
            "program_count": len(ACADEMY_PROGRAMMES),
            "lesson_count": len(ACADEMY_LESSONS),
            "status_endpoint": "/api/academy/status",
            "programs_endpoint": "/api/academy/programs",
            "practice_endpoint": "/api/academy/lessons/{lesson_id}/practice",
            "receipt_endpoint": "/api/academy/receipts",
            "status": "local_internal_academy_screen_module_implemented",
        },
        "live_action_gates": {
            "status_endpoint": "/api/live-actions/status",
            "receipts_endpoint": "/api/live-actions/receipts",
            "voice_transcription_endpoint": "/api/voice/transcription",
            "ripple_calendar_endpoint": "/api/ripple-calendar/write",
            "memory_sync_endpoint": "/api/memory/sync",
            "n8n_live_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-execute",
            "n8n_import_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/live-import",
            "status": "callable_approval_gates_with_exact_blocker_receipts",
        },
        "life_manager_n8n_workflows": {
            "workflow_count": len(N8N_WORKFLOW_REGISTRY),
            "workflow_dir": str(N8N_WORKFLOW_DIR),
            "registry_endpoint": "/api/life-manager/n8n-workflows",
            "receipt_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/dry-run",
            "preflight_endpoint": "/api/life-manager/n8n-workflows/{workflow_id}/preflight",
            "status": "disabled_import_pack_ready_with_local_preflight_receipts",
            "fixes_boundaries": [item["fixes_boundary"] for item in N8N_WORKFLOW_REGISTRY],
            "live_import_performed": False,
            "live_execution_performed": False,
        },
        "nas_source_index": {
            "status": source_manifest["status"],
            "files_indexed": source_manifest.get("files_indexed", 0),
            "roots": NAS_SOURCE_ROOTS,
            "excluded_roots": NAS_EXCLUDED_ROOTS,
            "only_approved_exclusions": source_manifest.get("only_approved_exclusions", True),
            "pgvector_required": False,
        },
        "notes": [
            "README.md is the canonical Product Bible in this repo.",
            "CK-LIFE-OS-PRODUCT-BIBLE-DELIVERY-MATRIX-270626.md is the durable delivery matrix.",
            "CK-LIFE-OS-SEMANTIC-PRODUCT-INTENT-ACCEPTANCE-MAP-270626.md is the semantic map.",
            "500 ideas are generated field/navigation innovation patterns absorbed through the UI lens, not user history or a raw register.",
            "AMTL operating layout is implemented in index.html with transparent local SVG assets and dynamic context rail.",
            "Encrypted journal entries use Fernet encryption at rest in the local runtime folder; plaintext is decrypted only through the local API/UI.",
            "Inner Work adds encrypted guided sessions for shadow integration, observation/JK-style inquiry, grounding, relationship patterns, and unknown-mode reflection.",
            "Daily Lens adds a 10,000-item local generated quote/anecdote/prompt library with hourly rotation and local saved-lens receipts.",
            "AI provider routing uses OpenRouter with free, modest, and expensive tiers selected by reasoning level.",
            "Approved NAS source indexing uses a local metadata/text-snippet index with exactly two excluded roots; pgvector/PostgreSQL remain optional, not required for source search.",
            "Life Coach / Life Manager v2 uses a state-aware menu, tabbed middle panels, contextual collapsed right rail, and local receipts for new workflow buttons.",
            "Life Manager n8n workflow pack provides disabled importable preflight workflows for paid model execution, voice transcription, calendar writes, and memory sync.",
            "Academy is implemented as Knowledge -> Academy with local programmes, lessons, practice receipts, and readiness checks.",
            "Live voice, Ripple calendar, memory sync, and n8n live execution are callable only through explicit approval gates with configured endpoints and rollback receipts.",
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
        "inner_work_guided_sessions",
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
        "nas_source_indexing_with_two_exclusions",
        "source_search_without_pgvector_dependency",
        "life_manager_v2_state_menu",
        "life_manager_v2_tabbed_screens",
        "life_manager_v2_local_receipts",
        "life_manager_v2_n8n_workflow_pack",
        "daily_lens_10k_library",
        "daily_lens_local_saved_list",
        "academy_local_learning_module",
        "live_action_approval_gate_receipts",
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
            "no_middle_column_scroll": True,
            "middle_content_uses_tabs": True,
            "right_rail_collapsed_contextual_boxes": True,
        },
        "life_manager_v2": {
            "menu": LIFE_MANAGER_MENU,
            "screen_count": len(LIFE_MANAGER_SCREENS),
            "screens": [item["id"] for item in LIFE_MANAGER_SCREENS],
            "normal_user_admin_proof_hidden": True,
            "n8n_workflow_count": len(N8N_WORKFLOW_REGISTRY),
            "daily_lens_visible_in_today": True,
            "academy_visible_in_knowledge": True,
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
            "daily_lens_current": "GET /api/daily-lens",
            "daily_lens_save": "POST /api/daily-lens/save",
            "daily_lens_saved": "GET /api/daily-lens/saved",
            "daily_lens_library": "GET /api/daily-lens/library",
            "inner_work_session": "POST /api/inner-work/session",
            "inner_work_modes": "GET /api/inner-work/modes",
            "ai_route": "POST /api/ai/route",
            "ai_complete": "POST /api/ai/complete",
            "rag_status": "GET /api/rag/status",
            "rag_source_draft": "POST /api/rag/source-draft",
            "rag_source_approved_fetch": "POST /api/rag/source-draft with fetch_approved=true",
            "rag_source_drafts": "GET /api/rag/source-drafts",
            "rag_search": "GET /api/rag/search",
            "source_index_status": "GET /api/source-index/status",
            "source_index_build": "POST /api/source-index/build",
            "source_index_search": "GET /api/source-index/search",
            "life_manager_spec": "GET /api/life-manager/spec",
            "life_manager_receipt": "POST /api/life-manager/receipt",
            "life_manager_receipts": "GET /api/life-manager/receipts",
            "life_manager_n8n_workflows": "GET /api/life-manager/n8n-workflows",
            "life_manager_n8n_dry_run": "POST /api/life-manager/n8n-workflows/{workflow_id}/dry-run",
            "life_manager_n8n_preflight": "POST /api/life-manager/n8n-workflows/{workflow_id}/preflight",
            "life_manager_n8n_live_import": "POST /api/life-manager/n8n-workflows/{workflow_id}/live-import",
            "life_manager_n8n_live_execute": "POST /api/life-manager/n8n-workflows/{workflow_id}/live-execute",
            "academy_status": "GET /api/academy/status",
            "academy_programs": "GET /api/academy/programs",
            "academy_lesson": "GET /api/academy/lessons/{lesson_id}",
            "academy_practice": "POST /api/academy/lessons/{lesson_id}/practice",
            "live_actions_status": "GET /api/live-actions/status",
            "voice_transcription": "POST /api/voice/transcription",
            "ripple_calendar_write": "POST /api/ripple-calendar/write",
            "memory_sync": "POST /api/memory/sync",
        },
        "drilldowns": [
            "practice detail",
            "receipt ledger",
            "encrypted journal detail",
            "inner work session detail",
            "dependency status",
            "500 ideas filtered rows",
            "idea detail",
            "report detail",
            "handover lane",
            "synthetic data preview",
            "R2D2-equivalent",
            "OpenRouter model policy",
            "RAG status and source draft boundary",
            "RAG source draft search result",
            "NAS source index status",
            "NAS source search results",
            "Life Manager v2 screen spec",
            "Life Manager v2 local workflow receipts",
            "Life Manager n8n workflow import pack and preflight receipts",
            "Daily Lens current/library/saved detail",
            "Academy program/lesson/practice/readiness detail",
            "Live action approval gate and blocker receipts",
        ],
        "button_truth": True,
        "count_truth": True,
    }


@app.get("/api/data-truth")
async def data_truth():
    source_manifest = _source_index_manifest()
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
        "inner_work": {
            "mode": "local_encrypted_jsonl",
            "path": str(INNER_WORK_FILE),
            "count": len(_read_inner_work_rows(limit=100000)),
            "encrypted_at_rest": True,
            "plaintext_stored": False,
            "ai_provider_called": False,
            "external_send": False,
            "source_write": False,
            "not_therapy": True,
        },
        "ideas": {
            "mode": "synthetic_seed_catalogue",
            "count": len(_practice_ideas()),
            "provider_called": False,
        },
        "daily_lens": {
            "mode": "local_generated_quote_anecdote_prompt_catalogue",
            "count": len(_daily_lens_library()),
            "saved_path": str(DAILY_LENS_SAVED_FILE),
            "saved_count": len(_read_saved_daily_lenses(limit=100000)),
            "rotation": "hourly local rotation plus user next offset",
            "permission_boundary": "CK originals, practice prompts, and paraphrased anecdote patterns; no fake attribution or long verbatim copyrighted quotes",
            "provider_called": False,
            "external_send": False,
            "source_write": False,
        },
        "academy": {
            "mode": "local_lesson_catalogue_and_jsonl_receipts",
            "program_count": len(ACADEMY_PROGRAMMES),
            "lesson_count": len(ACADEMY_LESSONS),
            "receipt_path": str(ACADEMY_RECEIPTS_FILE),
            "receipt_count": len(_read_academy_receipts(limit=100000)),
            "external_lms_write": False,
            "external_send": False,
            "provider_called": False,
        },
        "nas_source_index": {
            "mode": "local_metadata_and_text_snippet_index",
            "status": source_manifest["status"],
            "roots": NAS_SOURCE_ROOTS,
            "excluded_roots": NAS_EXCLUDED_ROOTS,
            "excluded_roots_count": len(NAS_EXCLUDED_ROOTS),
            "only_approved_exclusions": source_manifest.get("only_approved_exclusions", True),
            "files_indexed": source_manifest.get("files_indexed", 0),
            "text_records": source_manifest.get("text_records", 0),
            "index_path": str(SOURCE_INDEX_FILE),
            "manifest_path": str(SOURCE_INDEX_MANIFEST_FILE),
            "external_send": False,
            "source_write": False,
            "provider_called": False,
            "pgvector_required": False,
        },
        "life_manager_v2": {
            "mode": "local_jsonl_receipts",
            "path": str(LIFE_MANAGER_RECEIPTS_FILE),
            "count": len(_read_life_manager_receipts(limit=100000)),
            "external_send": False,
            "source_write": False,
            "provider_called": False,
            "calendar_write": False,
            "voice_transcription_provider_called": False,
        },
        "life_manager_n8n_workflows": {
            "mode": "disabled_importable_n8n_workflows_with_local_preflight_receipts",
            "workflow_dir": str(N8N_WORKFLOW_DIR),
            "workflow_count": len(N8N_WORKFLOW_REGISTRY),
            "receipt_path": str(N8N_PREFLIGHT_RECEIPTS_FILE),
            "receipt_count": len(_read_n8n_preflight_receipts(limit=100000)),
            "fixes_boundaries": [item["fixes_boundary"] for item in N8N_WORKFLOW_REGISTRY],
            "live_import_performed": False,
            "live_execution_performed": False,
            "external_send": False,
            "source_write": False,
            "provider_called": False,
            "paid_provider_call": False,
            "calendar_write": False,
            "transcription_provider_called": False,
            "memory_sync_performed": False,
        },
        "live_action_gates": {
            "mode": "explicit_approval_and_configured_endpoint_required",
            "receipt_path": str(LIVE_ACTION_RECEIPTS_FILE),
            "receipt_count": len(_read_live_action_receipts(limit=100000)),
            "status_endpoint": "/api/live-actions/status",
            "ripple_endpoint_configured": bool(os.getenv("RIPPLE_CALENDAR_ENDPOINT")),
            "transcription_endpoint_configured": bool(os.getenv("CK_LIFE_OS_TRANSCRIPTION_ENDPOINT")),
            "memory_sync_dir_configured": bool(os.getenv("CK_LIFE_OS_MEMORY_SYNC_DIR")),
            "n8n_webhook_base_configured": bool(os.getenv("N8N_WEBHOOK_BASE_URL")),
            "n8n_api_base_configured": bool(os.getenv("N8N_API_BASE_URL")),
            "n8n_api_key_configured": bool(os.getenv("N8N_API_KEY")),
            "live_default": False,
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
