from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


EVIDENCE_DIR = Path(
    r"C:\Users\Mani\AMTL-docs\AMTL-AGENT-CONTROL-CENTER\evidence\ck-life-os-local-internal-270626"
)


async def check_view(browser, name: str, url: str, viewport: dict[str, int]) -> dict:
    page = await browser.new_page(viewport=viewport)
    console_messages: list[dict] = []
    failed_requests: list[dict] = []
    bad_responses: list[dict] = []

    page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))
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

    await page.goto(url, wait_until="networkidle", timeout=30_000)
    screenshot = EVIDENCE_DIR / f"ck-life-os-workshop-registration-{name}.png"
    await page.screenshot(path=str(screenshot), full_page=True)

    data = await page.evaluate(
        """() => {
            const text = document.body.innerText;
            const buttons = [...document.querySelectorAll("button,a")]
                .map((b) => ({
                    text: (b.innerText || b.getAttribute("aria-label") || b.title || "").trim(),
                    disabled: !!b.disabled,
                    href: b.href || null
                }))
                .filter((b) => b.text);
            return {
                title: document.title,
                body_sample: text.slice(0, 1200),
                has_amtl: text.includes("AMTL") || text.includes("Almost Magic"),
                has_product: text.includes("CK Life OS") || text.includes("CK / Life OS"),
                has_seal: text.toLowerCase().includes("seal")
                    || !!document.querySelector('[alt*="seal" i], [src*="seal" i]'),
                has_contextual: text.includes("What")
                    && text.includes("Who")
                    && text.includes("Why")
                    && text.includes("ELI10"),
                has_reports: text.includes("Report") || text.includes("Evidence"),
                scroll_width: document.documentElement.scrollWidth,
                client_width: document.documentElement.clientWidth,
                horizontal_overflow: document.documentElement.scrollWidth
                    > document.documentElement.clientWidth + 2,
                button_count: buttons.length,
                buttons: buttons.slice(0, 40)
            };
        }"""
    )
    await page.close()

    data.update(
        {
            "view": name,
            "url": url,
            "viewport": viewport,
            "screenshot": str(screenshot),
            "console_errors": [msg for msg in console_messages if msg["type"] == "error"],
            "failed_requests": failed_requests,
            "bad_responses": bad_responses,
        }
    )
    data["pass"] = all(
        [
            not data["horizontal_overflow"],
            not data["console_errors"],
            not data["failed_requests"],
            not data["bad_responses"],
            data["has_product"],
            data["has_contextual"],
            data["has_reports"],
        ]
    )
    return data


async def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        views = [
            await check_view(
                browser,
                "desktop",
                "http://amtl/ck-life-os/",
                {"width": 1440, "height": 1000},
            ),
            await check_view(
                browser,
                "mobile",
                "http://amtl/lifeos/",
                {"width": 390, "height": 844},
            ),
        ]
        await browser.close()

    payload = {
        "checked_at": datetime.now().isoformat(),
        "product": "CK / Life OS",
        "scope": "Workshop and Beast registration browser QA",
        "pass": all(view["pass"] for view in views),
        "views": views,
    }
    output = EVIDENCE_DIR / "browser-qa-workshop-beast-registration.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(output),
                "pass": payload["pass"],
                "views": [
                    {
                        "view": view["view"],
                        "pass": view["pass"],
                        "screenshot": view["screenshot"],
                        "horizontal_overflow": view["horizontal_overflow"],
                        "button_count": view["button_count"],
                    }
                    for view in views
                ],
            },
            indent=2,
        )
    )
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
