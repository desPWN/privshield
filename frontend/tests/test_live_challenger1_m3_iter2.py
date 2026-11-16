import sys
import time
import socket
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_port(port, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

print("Starting backend server (port 8000)...")
backend_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", "8000"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

print("Starting frontend server (port 5173)...")
frontend_proc = subprocess.Popen(
    ["cmd.exe", "/c", "npx vite --host 127.0.0.1 --port 5173"],
    cwd="frontend",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

driver = None
failed = False
try:
    if not wait_for_port(8000, 20):
        raise RuntimeError("Backend failed to start on port 8000 within 20s")
    print("Backend listening on port 8000.")

    if not wait_for_port(5173, 20):
        raise RuntimeError("Frontend failed to start on port 5173 within 20s")
    print("Frontend listening on port 5173.")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=options)
    print("Headless Chrome initialized.")

    # -------------------------------------------------------------
    # PART 1: Root Document Overflow Containment Across Viewports
    # -------------------------------------------------------------
    print("\n--- PART 1: Root Document Overflow Containment Verification ---")
    driver.get("http://localhost:5173/#overview")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "root"))
    )
    time.sleep(1.5)

    resolutions = [
        (1920, 1080),
        (1440, 900),
        (1366, 768),
        (1280, 800)
    ]

    print(f"{'Resolution':<12} | {'html.overflowX':<16} | {'body.overflowX':<16} | {'#root.overflowX':<18} | {'scrollWidth':<12} | {'clientWidth':<12} | Status")
    print("-" * 105)

    for w, h in resolutions:
        driver.set_window_size(w, h)
        time.sleep(0.5)

        metrics = driver.execute_script("""
            const html = document.documentElement;
            const body = document.body;
            const root = document.getElementById('root');
            return {
                htmlOverflowX: window.getComputedStyle(html).overflowX,
                bodyOverflowX: window.getComputedStyle(body).overflowX,
                rootOverflowX: window.getComputedStyle(root).overflowX,
                scrollWidth: html.scrollWidth,
                clientWidth: html.clientWidth,
                scrollX: window.scrollX
            };
        """)

        html_ox = metrics["htmlOverflowX"]
        body_ox = metrics["bodyOverflowX"]
        root_ox = metrics["rootOverflowX"]
        sw = metrics["scrollWidth"]
        cw = metrics["clientWidth"]

        is_contained = (html_ox == "hidden" and body_ox == "hidden" and root_ox == "hidden")
        status = "PASS" if is_contained else "FAIL"
        if not is_contained:
            failed = True

        print(f"{f'{w}x{h}':<12} | {html_ox:<16} | {body_ox:<16} | {root_ox:<18} | {sw:<12} | {cw:<12} | {status}")

    # -------------------------------------------------------------
    # PART 2: DiscoveryView Runtime TypeError & Preview Table Test
    # -------------------------------------------------------------
    print("\n--- PART 2: DiscoveryView Preview Table Runtime Verification ---")
    
    # Load demo dataset
    print("Triggering Synthetic Demo Dataset Ingestion...")
    load_res = driver.execute_script("""
        return fetch('/api/datasets/load-industry-demo/healthcare', { method: 'POST' })
            .then(r => r.json());
    """)
    dataset_id = load_res.get("dataset_id")
    print(f"Loaded demo dataset ID: {dataset_id}")

    # Navigate to #discovery
    print("Navigating to #discovery...")
    driver.get("http://localhost:5173/#discovery")
    time.sleep(2.0)

    # Wait for tables
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )
    time.sleep(1.0)

    # Check preview table DOM
    table_info = driver.execute_script("""
        const tables = document.querySelectorAll('table');
        const headers = Array.from(document.querySelectorAll('h3')).map(h => h.innerText);
        const rows = document.querySelectorAll('tbody tr');
        return {
            tableCount: tables.length,
            headers: headers,
            rowCount: rows.length
        };
    """)
    print("Rendered Discovery tables info:", table_info)

    # Verify browser logs for any TypeError
    logs = driver.get_log("browser")
    severe_errors = [
        entry for entry in logs 
        if entry["level"] == "SEVERE" and "favicon" not in entry["message"]
    ]
    type_errors = [
        entry for entry in logs 
        if "TypeError" in entry["message"] or "Cannot read properties of undefined" in entry["message"]
    ]

    print("\nBrowser console SEVERE entries count:", len(severe_errors))
    if severe_errors:
        for err in severe_errors:
            print("  [SEVERE]", err["message"])

    print("Browser console TypeError count:", len(type_errors))
    if type_errors:
        for err in type_errors:
            print("  [TYPE_ERROR]", err["message"])
        failed = True
    else:
        print("[PASS] Zero TypeErrors encountered in browser during DiscoveryView preview rendering!")

    # Verify table row count > 0
    if table_info["rowCount"] > 0:
        print(f"[PASS] DiscoveryView preview table successfully rendered {table_info['rowCount']} rows!")
    else:
        print("[FAIL] Preview table rendered 0 rows.")
        failed = True

    # Test clicking "Reveal Raw Values"
    reveal_clicked = driver.execute_script("""
        const buttons = Array.from(document.querySelectorAll('button'));
        const btn = buttons.find(b => b.innerText.includes('Reveal Raw Values'));
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    """)
    print("Clicked 'Reveal Raw Values':", reveal_clicked)
    time.sleep(0.5)

    # Confirm modal if appeared
    driver.execute_script("""
        const modalBtns = Array.from(document.querySelectorAll('button'));
        const btn = modalBtns.find(b => b.innerText.includes('I Understand') || b.innerText.includes('Confirm') || b.innerText.includes('Reveal'));
        if (btn) btn.click();
    """)
    time.sleep(0.5)

    # Check logs again
    logs_after = driver.get_log("browser")
    after_type_errors = [
        e for e in logs_after 
        if "TypeError" in e["message"] or "Cannot read properties of undefined" in e["message"]
    ]
    if after_type_errors:
        print("[FAIL] TypeError after reveal toggle:", after_type_errors)
        failed = True
    else:
        print("[PASS] Zero TypeErrors encountered during interactive modal and reveal toggle!")

except Exception as ex:
    print(f"\n[EXCEPTION DURING LIVE VERIFICATION]: {ex}")
    failed = True
finally:
    if driver:
        driver.quit()
    print("\nCleaning up processes...")
    try:
        backend_proc.terminate()
        backend_proc.kill()
    except Exception:
        pass
    try:
        frontend_proc.terminate()
        frontend_proc.kill()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
    except Exception:
        pass
    print("Process cleanup complete.")

print("\n========================================================")
if failed:
    print("LIVE VERIFICATION RESULT: REJECT")
    sys.exit(1)
else:
    print("LIVE VERIFICATION RESULT: APPROVE (ALL LIVE CHECKS PASSED)")
    sys.exit(0)
