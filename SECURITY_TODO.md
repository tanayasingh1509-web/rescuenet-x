# 🚨 CRITICAL SECURITY REMEDIATION GUIDE (MANUAL STEPS REQUIRED)

This repository previously had a Google Maps API Key committed in commit history and source code.
Automated tools have removed all secrets from the active working tree, source code, environment templates, and frontend distribution bundles.

However, git history still contains previous commits, and Google Cloud credentials must be rotated manually by the project owner. The AI agent cannot perform actions outside the local repository.

Follow these 4 mandatory steps immediately:

---

## 1. Delete and Rotate the Leaked Google Maps Key
1. Go to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/google/maps-apis/credentials).
2. Locate the exposed Google Maps API key.
3. Click the **Delete** (Trash) icon to immediately revoke it and prevent unauthorized billing.
4. Click **+ CREATE CREDENTIALS** -> **API key** to generate a brand new, clean key.

---

## 2. Strictly Restrict the New API Key
Never leave an API key unrestricted.
1. Click on your newly created key to edit its settings.
2. Under **Application restrictions**:
   - Select **Websites (HTTP referrers)**.
   - Add your allowed deployment domains:
     - `http://localhost:*`
     - `http://127.0.0.1:*`
     - `https://your-production-domain.com/*`
     - `https://*.your-domain.com/*`
3. Under **API restrictions**:
   - Select **Restrict key**.
   - Check **ONLY** `Maps JavaScript API`.
   - Do **NOT** enable Geocoding, Places, Routes, or server-side APIs on a client-side browser key.
4. Click **Save**.

---

## 3. Set Quota Caps & Billing Budget Alerts
To guarantee protection against surprise billing:
1. Go to **Google Cloud Console** -> **Billing** -> **Budgets & alerts**.
2. Create a budget alert for your project (e.g., $1.00 / INR 100) with 50%, 90%, and 100% threshold notifications to your email.
3. Go to **APIs & Services** -> **Maps JavaScript API** -> **Quotas**.
4. Set a daily cap (e.g., maximum 1,000 requests per day) to prevent quota exhaustion or abuse.

---

## 4. Purge Git History (Optional but Recommended)
Because the key exists in previous git commits, you should purge it from history before making the repository public:

### Option A: Using `git-filter-repo` (Recommended by Git)
```bash
# 1. Install git-filter-repo
pip install git-filter-repo

# 2. Create a replacement file
echo "<LEAKED_KEY_REDACTED>==>REMOVED_LEAKED_KEY" > replace.txt

# 3. Purge the secret from all commits and branches
git filter-repo --replace-text replace.txt --force

# 4. Re-link your remote and force push (NOTE: rewrites git commit hashes)
git remote add origin https://github.com/tanayasingh1509-web/rescuenet-x.git
git push origin --force --all
```

### Option B: Using BFG Repo-Cleaner
```bash
# 1. Download BFG jar
# 2. Create text file with the leaked key
echo "<LEAKED_KEY_REDACTED>" > passwords.txt

# 3. Clean repository
java -jar bfg.jar --replace-text passwords.txt .git

# 4. Expire and prune reflog
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push origin --force --all
```

---

## 5. Enable Pre-Commit Hook Locally
To prevent accidental secret commits in the future:
```bash
git config core.hooksPath .githooks
```
This activates `.githooks/pre-commit`, running `scripts/check_secrets.py` on every `git commit`.
