"""
Keep Streamlit Community Cloud apps awake.

Streamlit Cloud puts apps to sleep after 12 hours of inactivity, and waking
them from inside an embedded iframe is blocked by third-party cookie policies
in modern browsers. A simple HTTP ping returns 200 but does not actually wake
the app because the front end is an SPA — JavaScript must execute and a
WebSocket must connect for the Python process to boot.

This script uses Playwright (headless Chromium) to:
  1. Visit each app URL.
  2. If the "Yes, get this app back up!" button is present, click it.
  3. Wait long enough for the boot sequence to complete.

Intended to be run on a schedule (every 6 hours) via GitHub Actions.
Exit code is 0 unless every app failed, so transient failures don't fail CI.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime

from playwright.async_api import async_playwright

APPS = [
    "https://4th-down-calculator.streamlit.app/",
    "https://4th-down-coach-explorer.streamlit.app/",
    "https://4th-down-heatmap.streamlit.app/",
]

WAKE_BUTTON_NAME = "Yes, get this app back up!"
NAV_TIMEOUT_MS = 45_000
POST_LOAD_WAIT_MS = 6_000
POST_WAKE_WAIT_MS = 60_000


async def visit(url: str, context) -> str:
    page = await context.new_page()
    try:
        await page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
        await page.wait_for_timeout(POST_LOAD_WAIT_MS)

        wake = page.get_by_role("button", name=WAKE_BUTTON_NAME)
        if await wake.count() > 0:
            await wake.click()
            await page.wait_for_timeout(POST_WAKE_WAIT_MS)
            return "WOKE"
        return "OK"
    except Exception as exc:  # pragma: no cover - best-effort keep-alive
        return f"FAIL ({exc.__class__.__name__})"
    finally:
        await page.close()


async def main() -> int:
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{stamp}] Visiting {len(APPS)} apps...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        results = await asyncio.gather(*(visit(url, context) for url in APPS))

        await context.close()
        await browser.close()

    for url, status in zip(APPS, results):
        print(f"  {status:<6} {url}")

    any_ok = any(r in ("OK", "WOKE") for r in results)
    return 0 if any_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
