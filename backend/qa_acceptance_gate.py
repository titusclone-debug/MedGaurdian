import asyncio
import json
import os
import sys
import time
from urllib.parse import urljoin

from playwright.async_api import async_playwright


BASE_URL = os.getenv("BASE_URL", "https://medgaurdian.onrender.com").rstrip("/")
MEDGUARDIAN_EMAIL = os.getenv("MEDGUARDIAN_EMAIL", "admin@stmarys.org")
MEDGUARDIAN_PASSWORD = os.getenv("MEDGUARDIAN_PASSWORD", "admin123")
HEADLESS = os.getenv("HEADLESS", "1") == "1"
SLOW_MO = 0 if HEADLESS else 100

MAX_LOGIN_SECONDS = float(os.getenv("MAX_LOGIN_SECONDS", "8"))
MAX_NABH_LOAD_SECONDS = float(os.getenv("MAX_NABH_LOAD_SECONDS", "15"))
MAX_EVIDENCE_TAB_SECONDS = float(os.getenv("MAX_EVIDENCE_TAB_SECONDS", "5"))


network = {
    "evidence_plan_calls": 0,
    "explanation_calls": 0,
    "legacy_compliance_calls": 0,
}

failures = []
warnings = []


def record_failure(message: str):
    print(f"  [FAIL] {message}")
    failures.append(message)


def record_warning(message: str):
    print(f"  [WARN] {message}")
    warnings.append(message)


def record_pass(message: str):
    print(f"  [PASS] {message}")


def api_url(path: str) -> str:
    return urljoin(f"{BASE_URL}/", path.lstrip("/"))


async def request_handler(request):
    url = request.url
    if "/api/nabh/requirements/" in url and "/evidence-plan" in url:
        network["evidence_plan_calls"] += 1
    if "/api/nabh/ontology/requirements/" in url and "/explanation" in url:
        network["explanation_calls"] += 1
    if "/api/nabh/compliance/" in url:
        network["legacy_compliance_calls"] += 1


async def api_get(page, path: str):
    return await page.evaluate(
        """async ({ path }) => {
            const token = localStorage.getItem('medguardian_token');
            const response = await fetch(path, {
                headers: token ? { Authorization: `Bearer ${token}` } : {}
            });
            let body = null;
            try { body = await response.json(); } catch (_) {}
            return { ok: response.ok, status: response.status, body };
        }""",
        {"path": path},
    )


async def api_post(page, path: str):
    return await page.evaluate(
        """async ({ path }) => {
            const token = localStorage.getItem('medguardian_token');
            const response = await fetch(path, {
                method: 'POST',
                headers: token ? { Authorization: `Bearer ${token}` } : {}
            });
            let body = null;
            try { body = await response.json(); } catch (_) {}
            return { ok: response.ok, status: response.status, body };
        }""",
        {"path": path},
    )


async def login(page):
    print("[1] Deployment & Login Baseline")
    start = time.perf_counter()

    await page.goto(BASE_URL, wait_until="domcontentloaded")

    try:
        await page.wait_for_selector("input[type='email']", timeout=10000)
        await page.fill("input[type='email']", MEDGUARDIAN_EMAIL)
        await page.fill("input[type='password']", MEDGUARDIAN_PASSWORD)
        await page.click("button:has-text('Sign In')")
    except Exception:
        record_warning("Login form not found; continuing in case session already exists.")

    try:
        await page.wait_for_selector("text=NABH Compliance", timeout=20000)
    except Exception:
        record_failure("Application shell did not appear after login.")
        return None

    seconds = time.perf_counter() - start
    if seconds > MAX_LOGIN_SECONDS:
        record_warning(f"Login/app shell took {seconds:.2f}s, above target {MAX_LOGIN_SECONDS:.2f}s.")
    else:
        record_pass(f"Login/app shell ready in {seconds:.2f}s.")

    user = await page.evaluate(
        """() => {
            const raw = localStorage.getItem('medguardian_user');
            return raw ? JSON.parse(raw) : null;
        }"""
    )
    if not user or not user.get("hospital_id"):
        record_failure("Could not read hospital_id from localStorage user session.")
        return None

    record_pass(f"Authenticated as {user.get('email')} for hospital_id={user.get('hospital_id')}.")
    return user


async def validate_seed_prerequisites(page):
    print("\n[2] Seed Prerequisites")

    editions = await api_get(page, "/api/nabh/ontology/editions")
    chapters = await api_get(page, "/api/nabh/ontology/chapters")
    requirements = await api_get(page, "/api/nabh/ontology/requirements?limit=100")
    coverage = await api_get(page, "/api/nabh/ontology/coverage")

    if not editions["ok"]:
        record_failure(f"/ontology/editions failed with {editions['status']}.")
    elif any(item.get("version") == "6.0" for item in editions["body"] or []):
        record_pass("Edition 6.0 exists.")
    else:
        record_failure("Edition 6.0 not found.")

    chapter_body = chapters["body"] if isinstance(chapters["body"], list) else []
    expected_chapters = {"AAC", "COP", "MOM", "PRE", "IPC", "PSQ", "ROM", "FMS", "HRM", "IMS"}
    found_chapters = {item.get("canonical_code") for item in chapter_body if isinstance(item, dict)}
    missing = sorted(expected_chapters - found_chapters)

    if chapters["ok"] and len(chapter_body) == 10 and not missing:
        record_pass("All 10 canonical chapters exist.")
    else:
        record_failure(f"Chapter seed invalid. Found={sorted(found_chapters)} Missing={missing}")

    req_body = requirements["body"] or {}
    if requirements["ok"] and req_body.get("total", 0) > 0 and len(req_body.get("items", [])) > 0:
        record_pass(f"Seeded requirements available: total={req_body.get('total')}.")
    else:
        record_failure("No seeded ontology requirements returned.")

    cov_body = coverage["body"] or {}
    if coverage["ok"] and cov_body.get("seeded_total_elements", 0) > 0:
        record_pass(f"Coverage has seeded elements: {cov_body.get('seeded_total_elements')}.")
    else:
        record_failure("Coverage endpoint shows zero seeded elements.")


async def validate_workspace_mount(page):
    print("\n[3] NABH Workspace Mount")
    start = time.perf_counter()

    try:
        # Navigate to home and click sidebar link to handle client-side SPA routing safely
        await page.click("text=NABH Compliance")
        await page.wait_for_selector("text=Hospital Profile", timeout=20000)
        seconds = time.perf_counter() - start
        if seconds > MAX_NABH_LOAD_SECONDS:
            record_failure(f"NABH workspace load critically slow: {seconds:.2f}s.")
        else:
            record_pass(f"NABH workspace mounted in {seconds:.2f}s.")
    except Exception as e:
        record_failure(f"NABH workspace failed to mount: {e}")

    try:
        await page.goto(f"{BASE_URL}/nabh?tab=evidence", wait_until="domcontentloaded")
        await page.wait_for_selector("text=NABH Accreditation Workspace", timeout=20000)
        await page.wait_for_selector("text=Evidence Needed", timeout=10000)
        body_text = await page.inner_text("body")
        if body_text.strip() == "Not Found":
            record_failure("Direct NABH deep link returned Render's Not Found page.")
        else:
            record_pass("Direct NABH deep link renders through the SPA fallback.")
    except Exception as e:
        record_failure(f"Direct NABH deep link failed to render: {e}")


async def validate_profile_and_scope(page, hospital_id: str):
    print("\n[4] Hospital Profile & Applicability")

    try:
        await page.click("button:has-text('Hospital Profile')")
        await page.wait_for_selector("text=Hospital Accreditation Profile", timeout=10000)
        await page.wait_for_selector("text=ICU", timeout=5000)
        await page.wait_for_selector("text=Operation Theatre", timeout=5000)
        record_pass("Profile scoping fields are visible.")
    except Exception as e:
        record_failure(f"Profile scoping fields are not visible: {e}")

    before = time.perf_counter()
    result = await api_post(page, f"/api/nabh/profile/{hospital_id}/compute-applicability")
    seconds = time.perf_counter() - before

    if result["ok"]:
        body = result["body"] or {}
        evaluated = body.get("total_requirements_evaluated", 0)
        if evaluated > 0:
            record_pass(f"Applicability computed across {evaluated} requirements in {seconds:.2f}s.")
        else:
            record_failure("Applicability returned 200 but evaluated zero requirements.")
    else:
        record_failure(f"Applicability computation failed with {result['status']}.")

    # Refresh frontend state by going to home and re-entering workspace
    try:
        await page.goto(BASE_URL)
        await page.click("text=NABH Compliance")
        await page.wait_for_selector("text=Hospital Profile", timeout=20000)
    except Exception as e:
        record_failure(f"Failed to refresh frontend state after computing applicability: {e}")

    req_state = await api_get(page, f"/api/nabh/requirements/{hospital_id}?limit=100")
    total = (req_state["body"] or {}).get("total", 0)
    if req_state["ok"] and total > 0:
        record_pass(f"Hospital requirement state exists: total={total}.")
    else:
        record_failure("Hospital requirement state did not populate after applicability computation.")


async def validate_browser_dom(page):
    print("\n[5] Standards Browser DOM")

    try:
        await page.click("button:has-text('Standards Browser')")
        await page.wait_for_selector("text=Official Chapters", timeout=10000)
        await page.wait_for_selector("text=Standards Browser", timeout=10000)
        record_pass("Standards Browser rendered.")
    except Exception as e:
        record_failure(f"Standards Browser did not render: {e}")


async def validate_evidence_performance(page):
    print("\n[6] Evidence Needed Performance & Network Assertions")

    network["evidence_plan_calls"] = 0
    network["explanation_calls"] = 0

    start = time.perf_counter()
    try:
        await page.click("button:has-text('Evidence Needed')")
        await page.wait_for_selector("text=Aggregated proof expectations", timeout=15000)
        seconds = time.perf_counter() - start
        if seconds > MAX_EVIDENCE_TAB_SECONDS:
            record_failure(f"Evidence tab too slow: {seconds:.2f}s.")
        else:
            record_pass(f"Evidence tab rendered in {seconds:.2f}s.")
    except Exception as e:
        seconds = time.perf_counter() - start
        record_failure(f"Evidence tab did not render aggregated proof expectations after {seconds:.2f}s: {e}")

    await page.wait_for_timeout(1500)

    if network["evidence_plan_calls"] >= 1:
        record_pass(f"Bulk evidence-plan endpoint fired {network['evidence_plan_calls']} time(s).")
    else:
        record_failure("Bulk evidence-plan endpoint never fired.")

    if network["explanation_calls"] == 0:
        record_pass("No /explanation N+1 calls fired during Evidence tab load.")
    else:
        record_failure(f"Detected {network['explanation_calls']} /explanation calls during Evidence tab load.")

    if network["legacy_compliance_calls"] == 0:
        record_pass("Legacy /api/nabh/compliance endpoint was not mounted.")
    else:
        record_failure(f"Legacy /api/nabh/compliance fired {network['legacy_compliance_calls']} time(s).")


async def validate_single_explanation(page):
    print("\n[7] Source-Cited Explanation Single-Call Check")

    try:
        await page.click("button:has-text('Applicable Requirements')")
        await page.wait_for_selector("button:has-text('Explain')", timeout=10000)
        before = network["explanation_calls"]
        await page.click("button:has-text('Explain')")
        await page.wait_for_selector("text=Requirement Explanation", timeout=10000)
        await page.wait_for_timeout(1000)
        after = network["explanation_calls"]

        if after == before + 1:
            record_pass("Intentional explanation opened with exactly one /explanation request.")
        else:
            record_failure(f"Explanation click made {after - before} /explanation requests; expected 1.")
    except Exception as e:
        record_failure(f"Could not open a single source-cited explanation from Applicable Requirements: {e}")


async def validate_readiness(page, hospital_id: str):
    print("\n[8] Readiness Denominator Verification")

    readiness = await api_get(page, f"/api/nabh/readiness/{hospital_id}")
    if not readiness["ok"]:
        record_failure(f"Readiness API failed with {readiness['status']}.")
        return

    r = readiness["body"] or {}
    denominator = r.get("denominator", 0)
    applicable = r.get("applicable_count", 0)
    conditional = r.get("conditional_count", 0)
    manual = r.get("manual_review_count", 0)
    not_applicable = r.get("not_applicable_count", 0)

    expected = applicable + conditional + manual
    if denominator == expected:
        record_pass(
            f"Readiness denominator is correct: {denominator} = "
            f"applicable({applicable}) + conditional({conditional}) + manual_review({manual}); "
            f"not_applicable({not_applicable}) excluded."
        )
    else:
        record_failure(f"Readiness denominator mismatch: got {denominator}, expected {expected}.")


async def validate_database_durability(page):
    print("\n[9] Database Durability & Seed Integrity Handshake")

    result = await api_get(page, "/api/admin/nabh-health")
    if not result["ok"]:
        record_failure(f"Diagnostic API /api/admin/nabh-health failed with status {result['status']}. Body: {result['body']}")
        return

    data = result["body"] or {}
    db_type = data.get("database_type")
    is_render = data.get("is_render")
    seed_status = data.get("nabh_seed_status", {})
    is_healthy = seed_status.get("is_healthy", False)

    print(f"  - Detected DB Dialect: {db_type}")
    print(f"  - Is Render Environment: {is_render}")
    print(f"  - Seeding Health Status: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")

    if is_render:
        # Enforce Postgres on Render (no SQLite in prod)
        if db_type == "postgresql":
            record_pass("Durable database backend verified: Managed PostgreSQL is active.")
        else:
            record_failure(f"Production durability violation: Ephemeral database type '{db_type}' detected on Render.")
    else:
        record_pass(f"Non-production backend type '{db_type}' verified.")

    if is_healthy:
        record_pass("NABH Phase 1 seed integrity verified: 10 chapters, active edition, and requirement coverage active.")
    else:
        record_failure(f"NABH ontology seed health check failed. Details: {seed_status}")


async def main():
    print("=" * 72)
    print("Task 20 NABH Phase 1 Acceptance Gate")
    print(f"Target: {BASE_URL}")
    print(f"Headless: {HEADLESS}")
    print("=" * 72)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = await browser.new_context()
        page = await context.new_page()
        page.on("request", request_handler)

        user = await login(page)
        if not user:
            await browser.close()
            sys.exit(1)

        hospital_id = user["hospital_id"]

        await validate_database_durability(page)
        await validate_workspace_mount(page)
        await validate_seed_prerequisites(page)

        if failures:
            print("\nFATAL: Seed/workspace prerequisites failed. Halting.")
            await browser.close()
            sys.exit(1)

        await validate_profile_and_scope(page, hospital_id)
        await validate_browser_dom(page)
        await validate_evidence_performance(page)
        await validate_single_explanation(page)
        await validate_readiness(page, hospital_id)

        await browser.close()

    print("\n" + "=" * 72)
    if failures:
        print(f"FINAL VERDICT: FAILED ({len(failures)} issue(s))")
        for item in failures:
            print(f" - {item}")
        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for item in warnings:
                print(f" - {item}")
        print("=" * 72)
        sys.exit(1)

    print("FINAL VERDICT: PASSED")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for item in warnings:
            print(f" - {item}")
    print("=" * 72)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
