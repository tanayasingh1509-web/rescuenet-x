#!/usr/bin/env python3
"""
RescueNet-X Public Tunnel & Server Launcher
Starts the Uvicorn FastAPI backend (which serves both backend APIs and the built frontend)
and exposes it to a public URL using Serveo / Pinggy.
"""

import sys
import os
import time
import re
import threading
import subprocess
import urllib.request
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def start_backend():
    import uvicorn
    # Bind to 0.0.0.0 on port 8000
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, log_level="warning")

def wait_for_backend(timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as res:
                if res.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def try_serveo_tunnel():
    print("[TUNNEL] Attempting to create public URL via Serveo (SSH)...", flush=True)
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=NUL",
        "-o", "ServerAliveInterval=30",
        "-o", "TCPKeepAlive=yes",
        "-R", "80:127.0.0.1:8000",
        "serveo.net"
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        url = None
        start = time.time()
        for line in iter(proc.stdout.readline, ''):
            print(f"  [serveo] {line.strip()}", flush=True)
            match = re.search(r'https?://[a-zA-Z0-9\.\-]+\.serveo[a-zA-Z0-9\.\-]+', line)
            if match:
                url = match.group(0).rstrip('.,;:')
                if not url.startswith("https://"):
                    url = url.replace("http://", "https://")
                return proc, url
            if time.time() - start > 15:
                break
        proc.terminate()
    except Exception as e:
        print(f"[TUNNEL] Serveo attempt failed: {e}", flush=True)
    return None, None

def try_pinggy_tunnel():
    print("[TUNNEL] Attempting to create public URL via Pinggy (SSH)...", flush=True)
    cmd = [
        "ssh",
        "-p", "443",
        "-R0:127.0.0.1:8000",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=NUL",
        "-o", "ServerAliveInterval=30",
        "-o", "TCPKeepAlive=yes",
        "a.pinggy.io"
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        url = None
        start = time.time()
        for line in iter(proc.stdout.readline, ''):
            print(f"  [pinggy] {line.strip()}", flush=True)
            match = re.search(r'https?://[a-zA-Z0-9\.\-]+pinggy[a-zA-Z0-9\.\-]+', line)
            if match and "dashboard.pinggy.io" not in match.group(0):
                url = match.group(0).rstrip('.,;:')
                if not url.startswith("https://"):
                    url = url.replace("http://", "https://")
                return proc, url
            if time.time() - start > 15:
                break
        proc.terminate()
    except Exception as e:
        print(f"[TUNNEL] Pinggy attempt failed: {e}", flush=True)
    return None, None

def main():
    print("=" * 65, flush=True)
    print("🚀 RESCUENET-X PUBLIC DEPLOYMENT LAUNCHER", flush=True)
    print("=" * 65, flush=True)

    # 1. Start FastAPI backend in background thread
    print("\n[Step 1] Starting backend server on http://0.0.0.0:8000...", flush=True)
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    if not wait_for_backend(timeout=20):
        print("❌ Failed to verify backend health check on port 8000.", flush=True)
        sys.exit(1)
    print("✓ Backend operational and serving frontend application.", flush=True)

    # 2. Establish public tunnel (Serveo -> Pinggy)
    print("\n[Step 2] Establishing secure public tunnel...", flush=True)
    tunnel_proc, public_url = try_serveo_tunnel()
    if not public_url:
        tunnel_proc, public_url = try_pinggy_tunnel()

    if not public_url:
        print("❌ Could not obtain public tunnel URL.", flush=True)
        sys.exit(1)

    print("\n" + "=" * 65, flush=True)
    print("🎉 RESCUENET-X IS LIVE AT PUBLIC URL:", flush=True)
    print(f"👉 Public URL: {public_url}", flush=True)
    print(f"👉 Command Dashboard: {public_url}/#/command", flush=True)
    print(f"👉 Citizen SOS Portal: {public_url}/#/citizen", flush=True)
    print(f"👉 API Health: {public_url}/health", flush=True)
    print("=" * 65, flush=True)
    print("\n[INFO] Keeping tunnel and server active.", flush=True)

    # Keep process alive and echo any incoming tunnel logs
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Terminating tunnel and server...", flush=True)
        if tunnel_proc:
            tunnel_proc.terminate()

if __name__ == "__main__":
    main()
