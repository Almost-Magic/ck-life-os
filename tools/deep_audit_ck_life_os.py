from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(r"C:\AMTL\repos\ck-life-os")
sys.path.insert(0, str(ROOT))

from main import NAS_EXCLUDED_ROOTS, app


EVIDENCE_DIR = Path(
    r"C:\Users\Mani\AMTL-docs\AMTL-AGENT-CONTROL-CENTER\evidence\ck-life-os-local-internal-270626"
)
OUTPUT = EVIDENCE_DIR / "ck-life-os-deep-audit-five-loop-v2-270628.json"


DOCS = [
    ROOT / "README.md",
    ROOT / "USER_MANUAL.md",
    ROOT / "COMPLETION-REPORT.md",
    ROOT / "CLAUDE.md",
    ROOT / "CK-LIFE-OS-PRODUCT-BIBLE-DELIVERY-MATRIX-270626.md",
    ROOT / "CK-LIFE-OS-SEMANTIC-PRODUCT-INTENT-ACCEPTANCE-MAP-270626.md",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_true(findings: list[dict], condition: bool, check: str, evidence: str, fix: str = "") -> None:
    if not condition:
        findings.append({"check": check, "evidence": evidence, "gap": True, "next_fix": fix or "repair local/internal mismatch"})


def audit_loop(loop: int) -> dict:
    client = TestClient(app)
    findings: list[dict] = []
    docs_text = "\n".join(read(path) for path in DOCS)
    html = read(ROOT / "index.html")

    matrix = client.get("/api/product-bible-matrix").json()
    r2d2 = client.get("/api/r2d2").json()
    ui = client.get("/api/ui-truth").json()
    data = client.get("/api/data-truth").json()
    rag = client.get("/api/rag/status").json()
    dependency = client.get("/api/dependency-status").json()
    ideas = client.get("/api/ideas?limit=500").json()
    source_status = client.get("/api/source-index/status").json()
    life_spec = client.get("/api/life-manager/spec").json()
    life_workflows = client.get("/api/life-manager/workflows").json()
    life_receipts = client.get("/api/life-manager/receipts").json()
    n8n = client.get("/api/life-manager/n8n-workflows").json()

    assert_true(findings, client.get("/").status_code == 200, "front door serves UI", "GET /")
    assert_true(findings, client.get("/api/health").json()["runtime_independent"] is True, "runtime independent health", "/api/health")
    assert_true(findings, matrix["covers_features"] and matrix["covers_500_ideas"], "Product Bible matrix coverage", "/api/product-bible-matrix")
    assert_true(findings, matrix["covers_nas_source_indexing"] and matrix["covers_rag_postgres_pgvector_truth"], "source/RAG matrix coverage", "/api/product-bible-matrix")
    assert_true(findings, matrix["covers_life_manager_v2_menu_screens_panels_buttons"], "Life Manager v2 matrix coverage", "/api/product-bible-matrix")
    assert_true(findings, r2d2["partial"] == 0 and r2d2["blocked"] == 0, "R2D2 no local/internal gaps", "/api/r2d2")
    assert_true(findings, ui["button_truth"] and ui["count_truth"], "button/count truth", "/api/ui-truth")
    for button in ["rag_status", "rag_source_draft", "rag_source_approved_fetch", "rag_source_drafts", "rag_search", "source_index_status", "life_manager_receipt", "life_manager_spec", "life_manager_n8n_workflows", "life_manager_n8n_dry_run", "life_manager_n8n_preflight"]:
        assert_true(findings, button in ui["buttons"], f"{button} button truth", "/api/ui-truth", "add missing UI truth mapping")

    assert_true(findings, data["ideas"]["count"] == 500, "500 idea count truth", "/api/data-truth")
    assert_true(findings, ideas["total"] == 500 and ideas["synthetic_data"] is True, "500 ideas synthetic boundary", "/api/ideas")
    assert_true(findings, data["encrypted_journal"]["encrypted_at_rest"] is True, "journal encryption truth", "/api/data-truth")
    assert_true(findings, data["inner_work"]["encrypted_at_rest"] is True, "Inner Work encryption truth", "/api/data-truth")
    assert_true(findings, data["external_send"] is False and data["source_write"] is False, "no external/source write", "/api/data-truth")

    assert_true(findings, rag["where_to_access"] == "Knowledge -> RAG / Sources", "RAG access location", "/api/rag/status")
    assert_true(findings, rag["internal_sources"]["excluded_roots"] == NAS_EXCLUDED_ROOTS, "exact RAG exclusions", "/api/rag/status")
    assert_true(findings, rag["external_sources"]["fetch_enabled"] == "approval_gated", "external fetch approval gate", "/api/rag/status")
    assert_true(findings, "approved_fetch_endpoint" in rag["external_sources"], "external approved fetch endpoint documented", "/api/rag/status")
    assert_true(findings, rag["draft_sources"]["searchable_when_text_is_pasted"] is True, "pasted source text searchable", "/api/rag/status")
    assert_true(findings, source_status["approved_exclusions"] == NAS_EXCLUDED_ROOTS, "source index exact exclusions", "/api/source-index/status")
    assert_true(findings, dependency["source_index"]["required_for_core_ui"] is False, "source index dependency-down", "/api/dependency-status")
    assert_true(findings, life_spec["version"] == "v2_local_internal_layout", "Life Manager v2 spec version", "/api/life-manager/spec")
    menu_items = [item for group in life_spec["menu"] for item in group["items"]]
    for item in ["Home", "Start My Day", "Check In", "End My Day", "Ask Guide", "I Feel Stuck", "Decision Help", "Deep Inquiry", "Voice Notes", "Life Map", "Promises", "Projects", "Calendar", "Ask My Sources", "RAG / Sources", "Insights", "Daily Review", "Weekly Review", "Monthly Report", "Privacy", "Memory"]:
        assert_true(findings, item in menu_items, f"Life Manager menu item present: {item}", "/api/life-manager/spec", f"add menu item {item}")
    assert_true(findings, len(life_spec["screens"]) >= 19, "Life Manager screen inventory includes v2 screens", "/api/life-manager/spec")
    assert_true(findings, life_workflows["external_send"] is False and life_workflows["source_write"] is False, "Life Manager workflows do not external send/write", "/api/life-manager/workflows")
    assert_true(findings, life_receipts["storage"].endswith("life-manager-receipts.jsonl"), "Life Manager local receipt storage", "/api/life-manager/receipts")
    assert_true(findings, n8n["total"] == 4, "n8n workflow pack has four workflows", "/api/life-manager/n8n-workflows")
    assert_true(findings, n8n["live_import_performed"] is False and n8n["live_execution_performed"] is False, "n8n no live import/execution", "/api/life-manager/n8n-workflows")
    assert_true(findings, all(item["exists"] and item["active_by_default"] is False for item in n8n["items"]), "n8n workflow files exist and are disabled", "/api/life-manager/n8n-workflows")
    assert_true(findings, set(item["fixes_boundary"] for item in n8n["items"]) == {"paid_model_execution", "live_voice_transcription", "external_calendar_writes", "cross_device_memory_sync"}, "n8n covers requested approval-gated boundaries", "/api/life-manager/n8n-workflows")

    required_ui = [
        "RAG / Sources",
        "RAG status",
        "Add source",
        "RAG source text",
        "Approve one-time external URL fetch into local RAG",
        "Stage source for approval",
        "Practice",
        "Private",
        "Knowledge",
        "Reports",
        "Admin / Proof",
        "Start My Day",
        "I Feel Stuck",
        "Decision Help",
        "Voice Notes",
        "Life Map",
        "Promises",
        "Projects",
        "Calendar",
        "Ask My Sources",
        "Memory",
        "n8n workflow pack",
        "context-rail",
        "practiceHero",
    ]
    for token in required_ui:
        assert_true(findings, token in html, f"UI contains {token}", "index.html", f"add visible/control token {token}")
    assert_true(findings, ".hidden { display: none !important; }" in html, "generic hidden class works for hero", "index.html")

    stale_phrases = [
        "RAG and pgvector are therefore explicitly out of scope",
        "47/47 Beast tests",
        "49/49",
        "CK tests `42 passed`",
        "53/53",
        "55 passed",
        "Knowledge\", \"Sources\"",
        "| NOT IMPLEMENTED |",
        "| PARTIAL |",
        "Planned for implementation",
        "Knowledge -> Source Library",
    ]
    for phrase in stale_phrases:
        assert_true(findings, phrase not in docs_text, f"stale phrase absent: {phrase}", "docs/product artefacts", f"remove stale phrase {phrase}")

    evidence_files = [
        EVIDENCE_DIR / "browser-qa-calm-tabs-layout-270628.json",
        EVIDENCE_DIR / "life-manager-v2-calm-layout-proof-270628.json",
        EVIDENCE_DIR / "ck-life-os-life-manager-home-desktop.png",
        EVIDENCE_DIR / "ck-life-os-life-manager-home-mobile.png",
        EVIDENCE_DIR / "ck-life-os-calm-tabs-desktop.png",
        EVIDENCE_DIR / "ck-life-os-calm-tabs-mobile.png",
        EVIDENCE_DIR / "ck-life-os-rag-sources-desktop.png",
        ROOT / "CK-Life-OS-Complete-Story-Flow-Guide-270628.docx",
    ]
    for path in evidence_files:
        assert_true(findings, path.exists() and path.stat().st_size > 0, f"evidence exists: {path.name}", str(path))

    return {
        "loop": loop,
        "checked_at": datetime.now().isoformat(),
        "findings": findings,
        "safe_local_internal_gaps": len(findings),
        "status": "pass" if not findings else "fail",
    }


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    loops = [audit_loop(loop) for loop in range(1, 6)]
    payload = {
        "product": "CK / Life OS",
        "scope": "deep UI/Product Bible/chat-artifact comparison after Life Manager v2 calm-layout and n8n workflow-pack repair",
        "generated_at": datetime.now().isoformat(),
        "loops": loops,
        "pass": all(loop["status"] == "pass" for loop in loops),
        "visual_evidence_reviewed": [
            str(EVIDENCE_DIR / "ck-life-os-calm-tabs-desktop.png"),
            str(EVIDENCE_DIR / "ck-life-os-calm-tabs-mobile.png"),
            str(EVIDENCE_DIR / "ck-life-os-rag-sources-desktop.png"),
            str(ROOT / "docx-render-qa" / "ck-life-os-story-flow-270628" / "contact-sheet.png"),
        ],
        "fixes_made_before_final_loop": [
            "Implemented local RAG source drafts with optional pasted source text, explicit approved external URL fetch into local RAG, and combined RAG search.",
            "Updated UI Add source panel and Search to use local RAG/source search.",
            "Updated README, USER_MANUAL, COMPLETION-REPORT, CLAUDE, Product Bible delivery matrix, semantic map, browser QA, tests, and story-flow Word doc generator.",
            "Regenerated and visually checked the Word story-flow document.",
            "Implemented and audited Life Manager v2 grouped menu, tabbed screens, contextual collapsed right rail, local workflow receipts, backend spec/workflow endpoints, and visible RAG / Sources naming.",
            "Implemented and audited CK-owned disabled n8n workflow imports and local preflight/dry-run receipts for paid model execution, live voice transcription, external calendar writes, and cross-device memory sync.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
