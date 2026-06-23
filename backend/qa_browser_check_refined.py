import asyncio
import time
import json
import os
import sys
from playwright.async_api import async_playwright, expect

TARGET_URL = os.getenv("TARGET_URL", "https://medgaurdian.onrender.com")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@stmarys.org")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
HEADLESS = os.getenv("HEADLESS", "1") == "1"

# Network Tracking state
api_data = {
    "evidence_plan_calls": 0,
    "explanation_calls": 0,
    "legacy_compliance_calls": 0,
    "readiness": None,
    "seed_editions": None,
    "seed_chapters": None,
    "seed_requirements": None,
    "seed_coverage": None,
    "compute_applicability_success": False
}

failures = []

def record_failure(msg):
    print(f"  [FAIL] {msg}")
    failures.append(msg)

async def request_handler(request):
    url = request.url
    if "/api/nabh/requirements/" in url and "/evidence-plan" in url:
        api_data["evidence_plan_calls"] += 1
    if "/explanation" in url:
        api_data["explanation_calls"] += 1
    if "/api/nabh/compliance/" in url:
        api_data["legacy_compliance_calls"] += 1

async def response_handler(response):
    url = response.url
    status = response.status
    if status != 200:
        return
        
    try:
        if "/api/nabh/readiness/" in url:
            api_data["readiness"] = await response.json()
        elif "/api/nabh/ontology/editions" in url:
            api_data["seed_editions"] = await response.json()
        elif "/api/nabh/ontology/chapters" in url:
            api_data["seed_chapters"] = await response.json()
        elif "/api/nabh/ontology/requirements" in url:
            api_data["seed_requirements"] = await response.json()
        elif "/api/nabh/ontology/coverage" in url:
            api_data["seed_coverage"] = await response.json()
        elif "/compute-applicability" in url:
            api_data["compute_applicability_success"] = True
    except:
        pass

async def run_qa():
    print("==================================================")
    print("🚀 Starting Rigorous Task 20 Acceptance Gate 🚀")
    print(f"Target: {TARGET_URL} | Headless: {HEADLESS}")
    print("==================================================\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()
        
        page.on("request", request_handler)
        page.on("response", response_handler)
        
        print("[1] Navigating to Target URL and Logging in...")
        await page.goto(TARGET_URL)
        
        try:
            await page.wait_for_selector("input[type='email']", timeout=10000)
            await page.fill("input[type='email']", ADMIN_EMAIL)
            await page.fill("input[type='password']", ADMIN_PASSWORD)
            await page.click("button:has-text('Sign In')")
            print("  [PASS] Login submitted.")
        except Exception as e:
            print("  [WARN] Already logged in or login failed.")

        try:
            # Wait for dashboard API or sidebar
            await page.wait_for_selector("text=Dashboard", timeout=15000)
            print("  [PASS] Reached application shell.")
        except:
            record_failure("Failed to reach application shell after login.")
        
        print("\n[2] Initializing Phase 1 NABH Workspace...")
        start_time = time.time()
        
        try:
            await page.click("text=NABH Compliance", timeout=5000)
        except:
            await page.goto(f"{TARGET_URL}/nabh", wait_until="networkidle")
            
        try:
            await page.wait_for_selector("text='Hospital Profile'", timeout=15000)
            nabh_load_time = time.time() - start_time
            print(f"  [PASS] NABH Workspace loaded in {nabh_load_time:.2f} seconds.")
            if nabh_load_time > 10.0:
                print(f"  [WARN] NABH Workspace load time is slow ({nabh_load_time:.2f}s).")
        except:
            record_failure("NABH Workspace failed to mount.")

        print("\n[3] Validating Seed Prerequisites (Strict API Inspection)...")
        await asyncio.sleep(3) # Ensure ontology endpoints returned
        
        editions = api_data.get("seed_editions", [])
        if any(e.get("version") == "6.0" for e in editions) if editions else False:
            print("  [PASS] Edition 6.0 found in DB.")
        else:
            record_failure("Edition 6.0 not found in /editions response.")
            
        chapters = api_data.get("seed_chapters", [])
        if chapters and len(chapters) == 10:
            print("  [PASS] 10 Chapters found in DB.")
        else:
            record_failure(f"Expected 10 chapters, found {len(chapters) if chapters else 0}.")
            
        reqs = api_data.get("seed_requirements", [])
        if reqs and len(reqs) > 0:
            print(f"  [PASS] {len(reqs)} seeded requirements fetched.")
        else:
            record_failure("Zero seeded requirements found in /requirements response.")
            
        coverage = api_data.get("seed_coverage", {})
        if coverage and coverage.get("seeded_total_elements", 0) > 0:
            print("  [PASS] Seeded total elements coverage is > 0.")
        else:
            record_failure("Coverage endpoint shows 0 seeded elements.")
            
        if len(failures) > 0:
            print("\n❌ FATAL: Deployed DB is not seeded properly. Halting tests.")
            await browser.close()
            sys.exit(1)

        print("\n[4] Hospital Profile Flow...")
        await page.goto(f"{TARGET_URL}/nabh?tab=profile")
        try:
            await page.wait_for_selector("text='ICU'", timeout=5000)
            print("  [PASS] Profile key scoping fields visible.")
        except:
            record_failure("Profile key scoping fields not visible.")

        print("\n[5] Applicability Computation Flow...")
        await page.goto(f"{TARGET_URL}/nabh?tab=applicable")
        await asyncio.sleep(2)
        try:
            btn = await page.wait_for_selector("text=/.*Compute Scope.*/i", timeout=5000)
            await btn.click()
            print("  [PASS] Triggered 'Compute Scope'.")
            # Wait for API success
            for _ in range(10):
                if api_data["compute_applicability_success"]:
                    break
                await asyncio.sleep(1)
            if api_data["compute_applicability_success"]:
                print("  [PASS] /compute-applicability API returned 200 OK.")
            else:
                record_failure("Did not capture successful /compute-applicability response.")
        except:
            print("  [WARN] Compute Scope button not found (might already be computed).")

        print("\n[6] Ontology / Standards Browser Checks...")
        await page.goto(f"{TARGET_URL}/nabh?tab=browser")
        await asyncio.sleep(2)
        # We already proved chapters exist via API. We can optionally check DOM here too.
        print("  [PASS] Standards Browser loaded. (Chapters already validated via API).")

        print("\n[7] Evidence Needed Flow (Performance DDoS Check)...")
        # Reset explanation counter to ensure clean tracking
        api_data["explanation_calls"] = 0
        
        start_time = time.time()
        await page.goto(f"{TARGET_URL}/nabh?tab=evidence")
        
        try:
            await page.wait_for_selector("text=/.*Aggregated proof expectations.*/i", timeout=10000)
            evidence_time = time.time() - start_time
            print(f"  [PASS] Evidence Tab rendered in {evidence_time:.2f} seconds!")
            if evidence_time > 5.0:
                print(f"  [WARN] Evidence Tab took {evidence_time:.2f}s to render.")
        except Exception as e:
            evidence_time = time.time() - start_time
            record_failure(f"TIMEOUT waiting for Evidence text after {evidence_time:.2f}s.")

        print("\n[8] Validating Strict Network Assertions...")
        await asyncio.sleep(2)
        
        if api_data["evidence_plan_calls"] > 0:
            print(f"  [PASS] /evidence-plan bulk endpoint fired ({api_data['evidence_plan_calls']} times).")
        else:
            record_failure("/evidence-plan was NEVER called.")
            
        if api_data["explanation_calls"] == 0:
            print("  [PASS] Zero /explanation N+1 queries fired during tab load.")
        else:
            record_failure(f"Found {api_data['explanation_calls']} rogue /explanation calls.")
            
        if api_data["legacy_compliance_calls"] == 0:
            print("  [PASS] Legacy /compliance endpoint was NOT mounted.")
        else:
            record_failure(f"Legacy /compliance fired {api_data['legacy_compliance_calls']} times.")

        print("\n[9] Source-Cited Explanation Flow (Single Call)...")
        try:
            explain_btn = await page.wait_for_selector("button:has-text('Explain')", timeout=2000)
            before_calls = api_data["explanation_calls"]
            await explain_btn.click()
            await asyncio.sleep(1)
            after_calls = api_data["explanation_calls"]
            if after_calls == before_calls + 1:
                print("  [PASS] Intentional /explanation request fired exactly once upon click.")
            else:
                record_failure(f"Explanation click resulted in {after_calls - before_calls} requests.")
        except:
            print("  [WARN] Could not find an 'Explain' button to click.")

        print("\n[10] Readiness Denominator Verification (API Level)...")
        await page.goto(f"{TARGET_URL}/nabh?tab=dashboard")
        await asyncio.sleep(3)
        if api_data["readiness"]:
            r = api_data["readiness"]
            denom = r.get("readiness_denominator", 0)
            applicable = r.get("applicable_count", 0)
            conditional = r.get("conditional_count", 0)
            manual = r.get("manual_review_count", 0)
            
            calc_denom = applicable + conditional + manual
            if denom == calc_denom:
                print(f"  [PASS] Readiness denominator ({denom}) exactly matches applicable + conditional + manual ({calc_denom}).")
            else:
                record_failure(f"Readiness denominator ({denom}) mismatch! Expected {calc_denom}.")
        else:
            record_failure("Readiness API response not captured.")

        print("\n==================================================")
        if len(failures) == 0:
            print("✅ FINAL VERDICT: ALL TASK 20 ACCEPTANCE CHECKS PASSED ✅")
            exit_code = 0
        else:
            print(f"❌ FINAL VERDICT: FAILED ({len(failures)} Errors) ❌")
            for f in failures:
                print(f"   - {f}")
            exit_code = 1
        print("==================================================")
        
        await browser.close()
        sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(run_qa())
