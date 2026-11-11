import os
import shutil
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\Admin\.gemini\antigravity\brain\0a519ffc-d33a-42c7-a143-1446d71020a8"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def capture_acceptance():
    print("Capturing acceptance screenshots on http://localhost:5173...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.goto("http://localhost:5173/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Quick sign-in if needed
        if page.locator("input[type='email']").is_visible():
            page.fill("input[type='email']", "ops@example.com")
            page.fill("input[type='password']", "OpsManager123!")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        # 1. Conflicts & Coverage Workspace
        print("Navigating to Conflicts Screen...")
        page.click("button:has-text('Conflicts & Coverage')")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        p1 = os.path.join(ARTIFACT_DIR, "acceptance-01-conflicts-resolved.png")
        page.screenshot(path=p1)
        print("Captured:", p1)

        # 2. Roster Calendar (30-day Month View)
        print("Navigating to Roster Calendar...")
        page.click("button:has-text('Roster Calendar')")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        # Ensure 30-day Month view is selected
        month_btn = page.locator("button:has-text('30-Day Month')")
        if month_btn.is_visible():
            month_btn.click()
            time.sleep(1.5)
        p2 = os.path.join(ARTIFACT_DIR, "acceptance-02-calendar-30day-resolved.png")
        page.screenshot(path=p2)
        print("Captured:", p2)

        # 3. Workforce Analytics
        print("Navigating to Workforce Analytics...")
        page.click("button:has-text('Workforce Analytics')")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        p3 = os.path.join(ARTIFACT_DIR, "acceptance-03-workforce-analytics.png")
        page.screenshot(path=p3)
        print("Captured:", p3)

        browser.close()
    print("Done capturing acceptance screenshots!")

if __name__ == "__main__":
    capture_acceptance()

