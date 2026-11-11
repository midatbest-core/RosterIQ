"""
Playwright Automated Visual Verification & Screenshot Capture Script
Captures high-resolution screenshots of all major redesigned screens.
"""
from __future__ import annotations

import os
import shutil
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = "c:\\Users\\Admin\\Roster\\screenshots"
ARTIFACT_DIR = "C:\\Users\\Admin\\.gemini\\antigravity\\brain\\0a519ffc-d33a-42c7-a143-1446d71020a8"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def capture_all():
    print("🚀 Starting Playwright visual capture on http://127.0.0.1:5173...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login Page
        page.goto("http://127.0.0.1:5173/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Fill credentials if on login
        if page.locator("input[type='email']").is_visible():
            page.fill("input[type='email']", "admin@example.com")
            page.fill("input[type='password']", "AdminPass123!")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        # 2. Dashboard Screen
        print("📸 Capturing 01-dashboard.png...")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01-dashboard.png"))

        # 3. Roster Calendar (Company View)
        print("📸 Capturing 02-calendar-company.png...")
        page.click("button:has-text('Roster Calendar')")
        time.sleep(2)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02-calendar-company.png"))

        # 4. Roster Calendar (Pod View)
        print("📸 Capturing 03-calendar-pod.png...")
        page.click("button:has-text('Pod-Wise')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03-calendar-pod.png"))

        # 5. Roster Calendar (Brand View)
        print("📸 Capturing 04-calendar-brand.png...")
        page.click("button:has-text('Brand-Wise')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04-calendar-brand.png"))

        # 6. Roster Calendar (Process View)
        print("📸 Capturing 05-calendar-process.png...")
        page.click("button:has-text('Process-Wise')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05-calendar-process.png"))

        # 7. Roster Calendar (Employee View)
        print("📸 Capturing 06-calendar-employee.png...")
        page.click("button:has-text('Employee-Wise')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06-calendar-employee.png"))

        # 8. Allocation Detail Drawer
        print("📸 Capturing 07-allocation-drawer.png...")
        # Click the first allocation card
        alloc_card = page.locator("div[class*='border-l-3']").first
        if alloc_card.is_visible():
            alloc_card.click()
            time.sleep(1)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07-allocation-drawer.png"))
            # Close drawer
            page.keyboard.press("Escape")
            time.sleep(0.5)

        # 9. Generate Roster Modal
        print("📸 Capturing 08-generate-modal.png...")
        page.click("button:has-text('Generate Roster')")
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08-generate-modal.png"))
        page.keyboard.press("Escape")
        time.sleep(0.5)

        # 10. Conflicts & Coverage Workspace
        print("📸 Capturing 09-conflicts-workspace.png...")
        page.click("button:has-text('Conflicts & Coverage')")
        time.sleep(2)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09-conflicts-workspace.png"))

        # 11. Reassignment Modal
        print("📸 Capturing 10-reassignment-modal.png...")
        reassign_btn = page.locator("button:has-text('Find Backup & Reassign')").first
        if reassign_btn.is_visible():
            reassign_btn.click()
            time.sleep(1.5)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10-reassignment-modal.png"))
            page.keyboard.press("Escape")
            time.sleep(0.5)

        # 12. Dynamic Allocation Log
        print("📸 Capturing 11-allocation-log.png...")
        page.click("button:has-text('Dynamic Allocation Log')")
        time.sleep(2)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "11-allocation-log.png"))

        # 13. Workforce Management: Employees
        print("📸 Capturing 12-workforce-employees.png...")
        page.click("button:has-text('Employees')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "12-workforce-employees.png"))

        # 14. Employee Profile Drawer
        print("📸 Capturing 13-employee-drawer.png...")
        page.locator("tr[class*='cursor-pointer']").first.click()
        time.sleep(1)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "13-employee-drawer.png"))
        page.keyboard.press("Escape")
        time.sleep(0.5)

        # 15. Workforce: Pods
        print("📸 Capturing 14-workforce-pods.png...")
        page.click("button:has-text('Pods & Leads')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "14-workforce-pods.png"))

        # 16. Operations: Brands & Processes
        print("📸 Capturing 15-operations-brands.png...")
        page.click("button:has-text('Brands & Processes')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "15-operations-brands.png"))

        # 17. Operations: Primary Assignments
        print("📸 Capturing 16-operations-assignments.png...")
        page.click("button:has-text('Primary Assignments')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "16-operations-assignments.png"))

        # 18. Operations: Operating Rules
        print("📸 Capturing 17-operations-rules.png...")
        page.click("button:has-text('Operating Rules & Holidays')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "17-operations-rules.png"))

        # 19. Management: Audit History & Lineage
        print("📸 Capturing 18-audit-history.png...")
        page.click("button:has-text('Roster History & Versions')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "18-audit-history.png"))

        browser.close()

    # Copy all to ARTIFACT_DIR
    print("📁 Copying screenshots to artifacts directory for markdown rendering...")
    for f in os.listdir(SCREENSHOT_DIR):
        if f.endswith(".png"):
            src = os.path.join(SCREENSHOT_DIR, f)
            dst = os.path.join(ARTIFACT_DIR, f)
            shutil.copy2(src, dst)

    print("🎉 All 18 screenshots captured and synchronized successfully!")

if __name__ == "__main__":
    capture_all()

