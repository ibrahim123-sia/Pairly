"""Take the README screenshots (1600x1200, 4:3) with Playwright.

Needs a running Pairly with the demo data (docker compose up, or the manual
quick start) and:
    pip install playwright
    python -m playwright install chromium

Usage:
    python docs/screenshots/capture_screenshots.py --base http://localhost:8080
    python docs/screenshots/capture_screenshots.py --base http://localhost:5173 --skip-ask

The Ask Pairly shot needs an LLM key on the backend; --skip-ask leaves it out.
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright

OUT = os.path.dirname(os.path.abspath(__file__))
VIEWPORT = {"width": 1600, "height": 1200}
BUNDLE_QUESTION = "What should I bundle with tea cups?"


def login(page, base, email, password, landing):
    page.goto(f"{base}/login")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.click("button[type=submit]")
    page.wait_for_url(f"**{landing}", timeout=30_000)


def shot(page, name):
    # Wait for toasts (e.g. "Welcome back!") to disappear first.
    toasts = page.locator("[role=status]")
    if toasts.count():
        toasts.first.wait_for(state="detached", timeout=10_000)
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path)
    print(f"saved {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--manager", default="demo@example.com:Demo@12345")
    ap.add_argument("--admin", default="admin@example.com:Admin@12345")
    ap.add_argument("--skip-ask", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---- store manager ----
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, color_scheme="light")
        page = ctx.new_page()
        login(page, base, *args.manager.split(":", 1), landing="/dashboard*")

        page.get_by_role("heading", name="AI Insights").wait_for(timeout=60_000)
        page.locator("section[aria-labelledby=ai-insights-title] ul li").first.wait_for(timeout=120_000)
        page.wait_for_load_state("networkidle")
        shot(page, "dashboard")

        if not args.skip_ask:
            page.goto(f"{base}/ask")
            page.get_by_role("button", name=BUNDLE_QUESTION).click()
            page.get_by_text("Tools used:").wait_for(timeout=120_000)
            page.wait_for_timeout(500)
            shot(page, "ask-pairly")

        page.goto(f"{base}/product-bundles")
        page.locator("table tbody tr").first.wait_for(timeout=120_000)
        page.wait_for_load_state("networkidle")
        shot(page, "bundles")

        page.goto(f"{base}/network-view")
        page.locator("canvas").first.wait_for(timeout=120_000)
        page.wait_for_load_state("networkidle")
        # Show the graph itself: scroll so its card heading sits at the top.
        page.get_by_text("Product Relationship Network").first.evaluate(
            "el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 90)")
        page.wait_for_timeout(6000)  # let the force layout settle
        shot(page, "network")

        page.goto(f"{base}/customers")
        page.get_by_text("Champions").first.wait_for(timeout=120_000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)  # chart animation
        shot(page, "customers-rfm")
        ctx.close()

        # ---- super admin ----
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, color_scheme="light")
        page = ctx.new_page()
        login(page, base, *args.admin.split(":", 1), landing="/admin**")
        page.goto(f"{base}/admin")
        page.get_by_role("heading", name="AI usage").wait_for(timeout=60_000)
        page.wait_for_load_state("networkidle")
        shot(page, "admin")
        ctx.close()

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
