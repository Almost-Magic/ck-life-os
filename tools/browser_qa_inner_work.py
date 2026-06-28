from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


EVIDENCE_DIR = Path(
    r"C:\Users\Mani\AMTL-docs\AMTL-AGENT-CONTROL-CENTER\evidence\ck-life-os-local-internal-270626"
)


async def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors: list[dict] = []
        failed_requests: list[dict] = []
        bad_responses: list[dict] = []
        page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type == "error" else None)
        page.on("requestfailed", lambda req: failed_requests.append({"url": req.url, "failure": req.failure.error_text if req.failure else "unknown"}))
        page.on("response", lambda resp: bad_responses.append({"url": resp.url, "status": resp.status}) if resp.status >= 400 else None)

        await page.goto("http://amtl/ck-life-os/", wait_until="networkidle", timeout=30_000)
        await page.get_by_role("button", name="Inner work").click()
        await page.select_option("#innerMode", "shadow")
        await page.fill("#innerIntention", "understand a reaction")
        await page.fill("#innerInput", "I felt angry when someone ignored me and I want to understand the rejected part.")
        await page.get_by_role("button", name="Start guided session").click()
        await page.wait_for_selector("#innerWorkDetail")
        await page.wait_for_timeout(300)
        screenshot = EVIDENCE_DIR / "ck-life-os-inner-work-desktop.png"
        await page.screenshot(path=str(screenshot), full_page=True)
        data = await page.evaluate(
            """() => {
                const body = document.body.innerText;
                return {
                    title: document.title,
                    has_inner_work: body.includes("Inner work"),
                    has_shadow: body.includes("Shadow integration"),
                    has_not_answer: body.includes("Not an answer:"),
                    has_first_question: body.includes("First question:"),
                    has_program: body.includes("Program:"),
                    has_ai_false: body.includes("AI provider called: false"),
                    has_external_false: body.includes("External send: false"),
                    horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
                    button_count: document.querySelectorAll("button").length
                };
            }"""
        )
        await browser.close()

    payload = {
        "checked_at": datetime.now().isoformat(),
        "product": "CK / Life OS",
        "scope": "Inner Work browser QA",
        "url": "http://amtl/ck-life-os/",
        "screenshot": str(screenshot),
        "console_errors": console_errors,
        "failed_requests": failed_requests,
        "bad_responses": bad_responses,
        **data,
    }
    payload["pass"] = all(
        [
            payload["has_inner_work"],
            payload["has_shadow"],
            payload["has_not_answer"],
            payload["has_first_question"],
            payload["has_program"],
            payload["has_ai_false"],
            payload["has_external_false"],
            not payload["horizontal_overflow"],
            not payload["console_errors"],
            not payload["failed_requests"],
            not payload["bad_responses"],
        ]
    )
    output = EVIDENCE_DIR / "browser-qa-inner-work-270628.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
