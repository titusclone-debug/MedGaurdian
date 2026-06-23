import asyncio
import time
from playwright.async_api import async_playwright

async def run_qa():
    print("Starting Task 20 Playwright E2E Manual QA Check...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        print("\n[1] Navigating to MedGaurdian Render URL...")
        await page.goto("https://medgaurdian.onrender.com/", wait_until="networkidle")
        
        # Login Flow
        print("[2] Executing Login Flow...")
        try:
            await page.wait_for_selector("input[type='email']", timeout=10000)
            await page.fill("input[type='email']", "admin@stmarys.org")
            await page.fill("input[type='password']", "admin123")
            await page.click("button:has-text('Sign In')")
            print("    -> Login submitted.")
        except Exception as e:
            print(f"    -> Login form not found or already logged in: {e}")

        print("\n[3] Waiting for Dashboard & Sidebar...")
        # Wait for either the dashboard text or the URL to change
        try:
            await page.wait_for_url("**/dashboard**", timeout=15000)
            print(f"    -> Reached dashboard URL: {page.url}")
        except Exception as e:
            print(f"    -> URL did not change to dashboard. Current URL: {page.url}")

        # Now try to find the NABH navigation link. It has href="/nabh".
        print("\n[4] NABH Entry Flow & Loading Ontology")
        start_time = time.time()
        try:
            await page.wait_for_selector("a[href='/nabh']", timeout=10000)
            await page.click("a[href='/nabh']")
        except Exception as e:
            print("    -> FAILED to find 'a[href=\"/nabh\"]' link. Attempting text fallback...")
            try:
                await page.click("text=NABH Compliance")
            except Exception as e2:
                print(f"    -> FAILED text fallback. Exiting. Current URL: {page.url}")
                await browser.close()
                return
        
        try:
            # We are now in the NABH workspace. Wait for Phase 1 indicator.
            await page.wait_for_selector("text='Hospital Profile'", timeout=15000)
            nabh_load_time = time.time() - start_time
            print(f"    -> NABH Workspace loaded in {nabh_load_time:.2f} seconds.")
        except Exception as e:
            print(f"    -> FAILED to load NABH Workspace. Are we on the Legacy Dashboard? Current URL: {page.url}")

        print("\n[5] Applicability Flow")
        try:
            await page.click("text='Applicable Requirements'")
            await asyncio.sleep(1)
            # Try to trigger compute if button exists
            compute_btn = await page.query_selector("text='Compute Applicability'")
            if compute_btn:
                await compute_btn.click()
                print("    -> Triggered Applicability Computation.")
                await asyncio.sleep(3)
            else:
                print("    -> 'Compute Applicability' button not found, assuming already computed.")
        except Exception as e:
            print("    -> Could not verify Applicability tab.")

        print("\n[6] Evidence Needed Flow & Performance DDoS Check")
        print("    -> Clicking 'Evidence Needed' tab (This triggers the 600 concurrent /explanation calls)...")
        start_time = time.time()
        try:
            await page.click("text='Evidence Needed'")
            await page.wait_for_selector("text='Mandatory'", timeout=30000)
            evidence_load_time = time.time() - start_time
            print(f"    -> Evidence Tab finally rendered in {evidence_load_time:.2f} seconds.")
        except Exception as e:
            evidence_load_time = time.time() - start_time
            print(f"    -> ⚠️ TIMEOUT OR CRASH during Evidence Load after {evidence_load_time:.2f} seconds.")

        print("\n[7] Readiness Flow")
        try:
            await page.click("text='Dashboard'")
            await page.wait_for_selector("text='Score'", timeout=10000)
            print("    -> Readiness dashboard loaded.")
        except:
            print("    -> Could not verify Readiness dashboard.")

        print("\nManual checks complete. Leaving browser open for 15 seconds for visual verification...")
        await asyncio.sleep(15)
        await browser.close()
        print("Browser closed. QA Complete.")

if __name__ == "__main__":
    asyncio.run(run_qa())
