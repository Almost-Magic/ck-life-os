from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


EVIDENCE_DIR = Path(
    r"C:\Users\Mani\AMTL-docs\AMTL-AGENT-CONTROL-CENTER\evidence\ck-life-os-local-internal-270626"
)


async def check_view(page, button_name: str, expected_panel: str) -> dict:
    await page.evaluate(
        """(name) => {
            const buttons = [...document.querySelectorAll("aside.left button")];
            const button = buttons.find(item => item.textContent.trim() === name);
            const group = button ? button.closest("details") : null;
            if (group) {
                [...document.querySelectorAll("aside.left details.menu-group")].forEach(item => item.open = item === group);
            }
        }""",
        button_name,
    )
    await page.locator("aside.left").get_by_role("button", name=button_name, exact=True).click()
    await page.wait_for_timeout(200)
    return await page.evaluate(
        """(expectedPanel) => {
            const view = document.querySelector(".view:not(.hidden)");
            const workspace = document.querySelector(".workspace");
            const tabPanels = view ? [...view.querySelectorAll(".tab-panel")] : [];
            const visiblePanels = tabPanels.filter(panel => !panel.classList.contains("hidden"));
            return {
                view_id: view ? view.id : null,
                expected_panel_visible: !!document.querySelector(`#${expectedPanel}:not(.hidden)`),
                tabbar_count: view ? view.querySelectorAll(".tabbar").length : 0,
                visible_tab_panels: visiblePanels.map(panel => panel.id),
                visible_panel_count: visiblePanels.length,
                workspace_overflow_y: getComputedStyle(workspace).overflowY,
                workspace_scrollable: workspace.scrollHeight > workspace.clientHeight + 2,
                horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
                practice_hero_hidden: expectedPanel === "practice" ? false : document.querySelector("#practiceHero").classList.contains("hidden"),
            };
        }""",
        expected_panel,
    )


async def run_for_viewport(playwright, viewport: dict, label: str) -> dict:
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page(viewport=viewport)
    console_errors: list[dict] = []
    failed_requests: list[dict] = []
    bad_responses: list[dict] = []
    page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type == "error" else None)
    page.on("requestfailed", lambda req: failed_requests.append({"url": req.url, "failure": req.failure.error_text if req.failure else "unknown"}))
    page.on("response", lambda resp: bad_responses.append({"url": resp.url, "status": resp.status}) if resp.status >= 400 else None)

    await page.goto("http://amtl/ck-life-os/", wait_until="networkidle", timeout=30_000)
    home_screenshot = EVIDENCE_DIR / f"ck-life-os-life-manager-home-{label}.png"
    await page.screenshot(path=str(home_screenshot), full_page=True)
    checks = []
    checks.append(await check_view(page, "Home", "today-start"))
    checks.append(await check_view(page, "Start My Day", "start-plan"))
    checks.append(await check_view(page, "Check In", "check-reality"))
    checks.append(await check_view(page, "End My Day", "end-done"))
    checks.append(await check_view(page, "Ask Guide", "ask-mode"))
    checks.append(await check_view(page, "I Feel Stuck", "stuck-name"))
    checks.append(await check_view(page, "Decision Help", "decision-options"))
    checks.append(await check_view(page, "Voice Notes", "voice-capture"))
    checks.append(await check_view(page, "Life Map", "life-values"))
    checks.append(await check_view(page, "Promises", "promise-active"))
    checks.append(await check_view(page, "Projects", "project-tasks"))
    checks.append(await check_view(page, "Calendar", "calendar-today"))
    checks.append(await check_view(page, "Ask My Sources", "ask-sources-question"))
    checks.append(await check_view(page, "Insights", "insight-patterns"))
    checks.append(await check_view(page, "Weekly Review", "weekly-promises"))
    checks.append(await check_view(page, "Memory", "memory-remembered"))
    checks.append(await check_view(page, "Practice desk", "practice"))
    checks.append(await check_view(page, "Encrypted journal", "journal-write"))
    checks.append(await check_view(page, "Inner work", "inner-start"))
    checks.append(await check_view(page, "Guide me", "guide-start"))
    checks.append(await check_view(page, "Innovation lens", "ideas-filter"))
    checks.append(await check_view(page, "RAG / Sources", "sources-status"))
    await page.get_by_role("button", name="Add source").click()
    rag_intake = await page.evaluate(
        """() => ({
            intake_visible: !!document.querySelector("#sources-intake:not(.hidden)"),
            source_type_present: !!document.querySelector("#ragSourceType"),
            source_text_present: !!document.querySelector("#ragSourceText"),
            fetch_approval_present: !!document.querySelector("#ragSourceFetchApproved"),
            stage_button_present: !!document.querySelector("#stageRagSource"),
            workspace_scrollable: document.querySelector(".workspace").scrollHeight > document.querySelector(".workspace").clientHeight + 2,
            horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
        })"""
    )
    checks.append(await check_view(page, "Reports and gates", "reports-summary"))
    await check_view(page, "Evidence summaries", "evidence-buttons")
    await page.get_by_role("button", name="n8n workflow pack").click()
    await page.wait_for_timeout(200)
    n8n_proof = await page.evaluate(
        """() => {
            const output = document.querySelector("#proofOutput")?.innerText || "";
            return {
                output,
                visible: !!document.querySelector("#evidence-output-panel:not(.hidden)"),
                has_workflow_count: output.includes("Workflows: 4"),
                has_no_live_import: output.includes("Live import performed: false"),
                has_no_live_execution: output.includes("Live execution performed: false"),
                has_openrouter: output.includes("OpenRouter paid execution"),
                has_voice: output.includes("voice transcription"),
                has_calendar: output.includes("calendar write"),
                has_memory: output.includes("memory sync"),
            };
        }"""
    )

    right_rail = await page.evaluate(
        """() => {
            const groups = [...document.querySelectorAll("aside.context-rail details")];
            const leftGroups = [...document.querySelectorAll("aside.left details.menu-group")];
            return {
                context_details_count: groups.length,
                context_open_count: groups.filter(item => item.open).length,
                left_group_count: leftGroups.length,
                left_open_count: leftGroups.filter(item => item.open).length,
                context_uses_details: groups.length >= 4,
                left_uses_details: leftGroups.length >= 2,
            };
        }"""
    )
    screenshot = EVIDENCE_DIR / f"ck-life-os-calm-tabs-{label}.png"
    await page.screenshot(path=str(screenshot), full_page=True)
    await browser.close()

    return {
        "label": label,
        "viewport": viewport,
        "home_screenshot": str(home_screenshot),
        "screenshot": str(screenshot),
        "console_errors": console_errors,
        "failed_requests": failed_requests,
        "bad_responses": bad_responses,
        "checks": checks,
        "right_rail": right_rail,
        "pass": all(
            [
                not console_errors,
                not failed_requests,
                not bad_responses,
                right_rail["context_uses_details"],
                right_rail["left_uses_details"],
                right_rail["context_open_count"] <= 1,
                all(item["expected_panel_visible"] for item in checks),
                all(item["tabbar_count"] >= 1 for item in checks),
                all(item["visible_panel_count"] <= 1 for item in checks),
                all(item["workspace_overflow_y"] == "hidden" for item in checks),
                all(item["practice_hero_hidden"] for item in checks if item["view_id"] != "practice"),
                rag_intake["intake_visible"],
                rag_intake["source_type_present"],
                rag_intake["source_text_present"],
                rag_intake["fetch_approval_present"],
                rag_intake["stage_button_present"],
                not rag_intake["workspace_scrollable"],
                not rag_intake["horizontal_overflow"],
                n8n_proof["visible"],
                n8n_proof["has_workflow_count"],
                n8n_proof["has_no_live_import"],
                n8n_proof["has_no_live_execution"],
                n8n_proof["has_openrouter"],
                n8n_proof["has_voice"],
                n8n_proof["has_calendar"],
                n8n_proof["has_memory"],
                not any(item["horizontal_overflow"] for item in checks),
            ]
        ),
        "rag_intake": rag_intake,
        "n8n_proof": n8n_proof,
    }


async def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        desktop = await run_for_viewport(playwright, {"width": 1440, "height": 1000}, "desktop")
        mobile = await run_for_viewport(playwright, {"width": 390, "height": 844}, "mobile")

    payload = {
        "checked_at": datetime.now().isoformat(),
        "product": "CK / Life OS",
        "scope": "calm tabs layout QA",
        "url": "http://amtl/ck-life-os/",
        "desktop": desktop,
        "mobile": mobile,
    }
    payload["pass"] = desktop["pass"] and mobile["pass"]
    output = EVIDENCE_DIR / "browser-qa-calm-tabs-layout-270628.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
