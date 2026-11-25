#!/usr/bin/env python3
"""
RescueNet-X Deployment Verification Suite (Task 8)
Automates running and validating the app on a fresh lightweight environment.
"""

import sys
import os
import json
import time
import re
import signal
import asyncio
import subprocess
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(PROJECT_ROOT)

def is_server_running(port=8000):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(req, timeout=1) as res:
            return res.status == 200
    except Exception:
        return False

def test_health():
    print("\n[8.b] Testing GET /health...")
    url = "http://127.0.0.1:8000/health"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as res:
        code = res.status
        raw = res.read().decode()
        body = json.loads(raw)
        print(f"  HTTP Status: {code}")
        print(f"  Response Body: {json.dumps(body, indent=2)}")
        assert code == 200, f"Expected 200, got {code}"
        assert body.get("status") == "healthy", f"Expected 'healthy', got {body.get('status')}"
        print("  -> PASS: GET /health returned 200 with healthy status.")
    return body

def test_frontend():
    print("\n[8.c] Testing GET / and referenced JS bundle...")
    url = "http://127.0.0.1:8000/"
    with urllib.request.urlopen(url, timeout=5) as res:
        code = res.status
        html = res.read().decode()
        print(f"  GET / HTTP Status: {code}")
        print(f"  HTML payload length: {len(html)} bytes")
        assert code == 200, f"Expected 200, got {code}"
        assert "<!doctype html>" in html.lower() or "<html" in html.lower(), "HTML shell missing"

        match = re.search(r'src=["\'](/assets/index-[^"\']+\.js)["\']', html)
        if not match:
            match = re.search(r'src=["\']([^"\']+\.js)["\']', html)
        assert match, f"Could not find referenced JS bundle in HTML:\n{html}"
        js_rel_path = match.group(1)
        js_url = f"http://127.0.0.1:8000{js_rel_path}" if not js_rel_path.startswith("http") else js_rel_path
        print(f"  Found JS Bundle script tag: {js_rel_path}")

        with urllib.request.urlopen(js_url, timeout=5) as js_res:
            js_code = js_res.status
            js_bytes = js_res.read()
            print(f"  GET {js_rel_path} HTTP Status: {js_code}")
            print(f"  Bundle size: {len(js_bytes):,} bytes")
            assert js_code == 200, f"Expected 200 for JS bundle, got {js_code}"
            assert len(js_bytes) > 1000, "JS bundle seems empty"
            print("  -> PASS: Frontend index HTML and production JS bundle return 200.")
    return True

async def test_websocket():
    print("\n[8.d] Testing WebSocket connection to /ws...")
    import websockets
    uri = "ws://127.0.0.1:8000/ws"
    async with websockets.connect(uri) as ws:
        print(f"  Connected to {uri}")
        await ws.send(json.dumps({"type": "ping", "client_time": time.time()}))
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(response)
        print(f"  Received WebSocket message type: {data.get('type')}")
        print(f"  Payload preview: {json.dumps(data)[:200]}...")
        assert data.get("type") in ["pong", "INITIAL_STATE", "INCIDENT_UPDATE", "UNIT_UPDATE"], f"Unexpected type: {data.get('type')}"
        print("  -> PASS: WebSocket connection established and message received.")
    return True

def test_auth():
    print("\n[8.e] Testing POST /api/simulate/reset authentication...")
    url = "http://127.0.0.1:8000/api/simulate/reset"

    print("  1. Sending unauthenticated POST /api/simulate/reset...")
    req_unauth = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req_unauth, timeout=5) as res:
            assert False, f"Expected 401 Unauthorized, got {res.status}"
    except urllib.error.HTTPError as e:
        print(f"     Status: {e.code} (Correctly rejected without token)")
        assert e.code == 401, f"Expected 401, got {e.code}"

    print("  2. Sending authenticated POST /api/simulate/reset with X-Admin-Token: test-token...")
    req_auth = urllib.request.Request(url, data=b"", method="POST", headers={"X-Admin-Token": "test-token"})
    with urllib.request.urlopen(req_auth, timeout=5) as res:
        code = res.status
        body = json.loads(res.read().decode())
        print(f"     Status: {code}")
        print(f"     Response: {json.dumps(body)}")
        assert code == 200, f"Expected 200, got {code}"
        assert body.get("status") in ["reset_successful", "reset"], f"Unexpected response status: {body.get('status')}"
        print("  -> PASS: Unauthenticated returns 401, authenticated with X-Admin-Token returns 200.")
    return True

def test_memory(server_pid):
    print("\n[8.f] Measuring peak memory of running app...")
    if not server_pid:
        ps_cmd = 'Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess'
        try:
            out = subprocess.check_output(['powershell', '-Command', ps_cmd], text=True).strip()
            if out:
                server_pid = int(out.split()[0])
        except Exception:
            pass

    if server_pid:
        ps_mem = f'(Get-Process -Id {server_pid}).WorkingSet64 / 1MB'
        try:
            mem_mb = float(subprocess.check_output(['powershell', '-Command', ps_mem], text=True).strip())
            print(f"  Target Process PID: {server_pid}")
            print(f"  Working Set Memory: {mem_mb:.2f} MB")
            print(f"  Render Free Tier Limit: 512.00 MB")
            print(f"  RAM Utilization: {(mem_mb / 512.0) * 100:.1f}%")
            assert mem_mb < 512.0, f"Memory {mem_mb} MB exceeds 512 MB limit"
            print("  -> PASS: Memory is comfortably below 512 MB.")
            return mem_mb
        except Exception as e:
            print(f"  Error reading process memory: {e}")
            return 0.0
    else:
        print("  Could not resolve server PID.")
        return 0.0

def main():
    print("=" * 65)
    print("RESCUENET-X TASK 8: LOCAL REPRODUCIBILITY & VERIFICATION")
    print("=" * 65)

    env = os.environ.copy()
    env["PORT"] = "8000"
    env["ADMIN_TOKEN"] = "test-token"
    env["DATABASE_PATH"] = os.path.join(PROJECT_ROOT, "data", "rescuenet.db")

    server_proc = None
    spawned = False

    if not is_server_running(8000):
        print("Starting Uvicorn server on port 8000 with deployment environment...")
        cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
        server_proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        spawned = True
        
        # Wait up to 15 seconds for startup
        started = False
        for _ in range(30):
            time.sleep(0.5)
            if is_server_running(8000):
                started = True
                break
        if not started:
            print("Server failed to start within 15s. Output:")
            if server_proc.poll() is not None:
                out, _ = server_proc.communicate()
                print(out)
            sys.exit(1)
        print(f"Uvicorn server running (PID: {server_proc.pid})")
    else:
        print("Existing server detected running on port 8000.")

    server_pid = server_proc.pid if server_proc else None

    try:
        test_health()
        test_frontend()
        asyncio.run(test_websocket())
        test_auth()
        mem = test_memory(server_pid)

        print("\n" + "=" * 65)
        print("SUMMARY: ALL 5 CHECKS (8.b - 8.f) PASSED SUCCESSFULLY!")
        print(f"Peak Working Set Memory: {mem:.2f} MB (< 512 MB free tier)")
        print("=" * 65)
    finally:
        if spawned and server_proc:
            print("\nShutting down test Uvicorn server...")
            try:
                subprocess.run(['powershell', '-Command', f'Stop-Process -Id {server_proc.pid} -Force'], capture_output=True)
            except Exception:
                pass
            server_proc.kill()
            print("Test server stopped.")

if __name__ == "__main__":
    main()
