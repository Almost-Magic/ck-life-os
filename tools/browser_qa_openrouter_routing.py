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

        page.on(
            "console",
            lambda msg: console_errors.append({"type": msg.type, "text": msg.text})
            if msg.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda req: failed_requests.append(
                {"url": req.url, "failure": req.failure.error_text if req.failure else "unknown"}
            ),
        )
        page.on(
            "response",
            lambda resp: bad_responses.append({"url": resp.url, "status": resp.status})
            if resp.status >= 400
            else None,
        )

        await page.goto("http://amtl/ck-life-os/", wait_until="networkidle", timeout=30_000)
        await page.get_by_text("Admin / Proof").click()
        await page.get_by_role("button", name="OpenRouter routing").click()
        await page.wait_for_selector("#proofOutput")
        await page.wait_for_timeout(300)

        screenshot = EVIDENCE_DIR / "ck-life-os-openrouter-proof-desktop.png"
        await page.screenshot(path=str(screenshot), full_page=True)

        data = await page.evaluate(
            """() => {
                const proof = document.querySelector("#proofOutput")?.innerText || "";
                const status = document.querySelector("#statusLine")?.innerText || "";
                return {
                    title: document.title,
                    status_line: status,
                    proof_output: proof,
                    has_provider: proof.includes("Provider: openrouter"),
                    has_routing: proof.includes("free -> modest -> expensive"),
                    has_boundary: proof.includes("No provider call occurs"),
                    horizontal_overflow: document.documentElement.scrollWidth
                        > document.documentElement.clientWidth + 2,
                    button_count: document.querySelectorAll("button").length
                };
            }"""
        )
        await browser.close()

    payload = {
        "checked_at": datetime.now().isoformat(),
        "product": "CK / Life OS",
        "scope": "OpenRouter proof button browser QA",
        "url": "http://amtl/ck-life-os/",
        "screenshot": str(screenshot),
        "console_errors": console_errors,
        "failed_requests": failed_requests,
        "bad_responses": bad_responses,
        **data,
    }
    payload["pass"] = all(
        [
            payload["has_provider"],
            payload["has_routing"],
            payload["has_boundary"],
            not payload["horizontal_overflow"],
            not payload["console_errors"],
            not payload["failed_requests"],
            not payload["bad_responses"],
        ]
    )
    output = EVIDENCE_DIR / "browser-qa-openrouter-routing-270626.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
