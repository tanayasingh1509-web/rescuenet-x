#!/usr/bin/env python3
"""
scripts/check_secrets.py - Pre-commit and CI scanner for leaked secrets & API keys.
Scans the repository working tree for known API credential patterns.
"""

import sys
import re
from pathlib import Path

# Directories and files to skip
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist-ssr"
}

# High-confidence secret patterns
SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z_-]{30,}", "Google API Key (AIza...)"),
    (r"pk\.eyJ[a-zA-Z0-9_-]{10,}", "Mapbox Public Token (pk.eyJ...)"),
    (r"sk-[a-zA-Z0-9_-]{20,}", "Secret Key (sk-...)"),
    (r"AC[0-9a-fA-F]{32}", "Twilio Account SID (AC...)"),
    (r"GOCSPX-[a-zA-Z0-9_-]{20,}", "Google OAuth Secret (GOCSPX-...)"),
]

COMPILED_PATTERNS = [(re.compile(pat), desc) for pat, desc in SECRET_PATTERNS]

def is_binary_file(filepath: Path) -> bool:
    try:
        with open(filepath, "tr") as check_file:
            check_file.read(1024)
            return False
    except UnicodeDecodeError:
        return True

def scan_file(filepath: Path):
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                for pattern, desc in COMPILED_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        matched_str = match.group(0)
                        masked = matched_str[:4] + "••••" + matched_str[-4:]
                        violations.append((line_no, desc, masked))
    except Exception as e:
        pass
    return violations

def main():
    root_dir = Path(__file__).resolve().parent.parent
    has_violations = False
    scanned_count = 0

    for path in root_dir.rglob("*"):
        if path.is_file():
            # Check exclusions
            if any(p in EXCLUDE_DIRS or p.startswith(".venv") or p.startswith("venv") for p in path.parts):
                continue
            # Skip check_secrets.py itself and documentation of patterns
            if path.name in ("check_secrets.py", "SECURITY_TODO.md"):
                continue
            if is_binary_file(path):
                continue

            scanned_count += 1
            violations = scan_file(path)
            if violations:
                has_violations = True
                for line_no, desc, masked in violations:
                    rel_path = path.relative_to(root_dir)
                    print(f"❌ [SECRET FOUND] {rel_path}:{line_no} -> {desc}: {masked}", file=sys.stderr)

    if has_violations:
        print("\n[FAILED] Leaked secrets or live credentials detected in source tree!", file=sys.stderr)
        print("Please remove secrets and use environment variables before committing.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✅ Secret scan passed: {scanned_count} files verified clean.")
        sys.exit(0)

if __name__ == "__main__":
    main()
