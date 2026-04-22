# Deploying SoilSense to Streamlit Cloud

The free tier of Streamlit Community Cloud is more than enough for a portfolio demo. The whole setup takes about 20 minutes, most of which is the one-time Google Earth Engine service-account dance.

---

## Prerequisites

- A GitHub account with the repo pushed (public is easiest)
- A Google account
- About 20 minutes

---

## Step 1 — Push the repo to GitHub

```bash
cd soilsense
git init
git add .
git commit -m "Initial SoilSense dashboard"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/soilsense.git
git push -u origin main
```

Verify on GitHub that these files did NOT get committed (they're in `.gitignore` but double-check):
- `.streamlit/secrets.toml`
- Any `*.json` service-account keys
- `data/cache/`, `data/raw/`

If any of these leaked, rotate the credentials immediately.

---

## Step 2 — Deploy the app shell (before GEE auth)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **New app**.
3. Fill in:
   - **Repository:** `YOUR-USERNAME/soilsense`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** pick a subdomain, e.g. `soilsense`
4. Click **Deploy**.

The first build takes 3–5 minutes while Streamlit installs geopandas, rasterio, and friends. The app will come up with a yellow indicator for Earth Engine (offline) in the sidebar — that's expected for now. SoilGrids calls should work immediately.

If the build fails, check the logs for a version conflict — if that happens, re-read the pinned versions in `requirements.txt` and make sure you haven't loosened any.

---

## Step 3 — Set up a Google Earth Engine service account

This is the only tricky part. Do it once and forget about it.

### 3a. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Create a new project — name it e.g. `soilsense-demo`. Note the project ID.

### 3b. Enable the Earth Engine API

1. In the Cloud Console, open **APIs & Services → Library**.
2. Search for **Earth Engine API** and click **Enable**.

### 3c. Create a service account

1. Go to **IAM & Admin → Service Accounts → Create Service Account**.
2. Name it `soilsense-app`. The email will be something like `soilsense-app@soilsense-demo.iam.gserviceaccount.com`.
3. Grant it the **Earth Engine Resource Viewer** role (or Editor if you plan to export assets).
4. Click **Done**.
5. Click on the new service account, go to the **Keys** tab, click **Add Key → Create new key → JSON**.
6. A JSON file will download. Keep it safe — this is the credential you'll paste into Streamlit.

### 3d. Register the service account with Earth Engine

1. Go to [signup.earthengine.google.com/#!/service_accounts](https://signup.earthengine.google.com/#!/service_accounts).
2. Paste the service-account email.
3. Accept the terms.

This is the step most people miss. Without it, authentication will succeed but every API call will return a permission error.

---

## Step 4 — Add secrets to Streamlit Cloud

1. On [share.streamlit.io](https://share.streamlit.io), open your app.
2. Click the **⋮** menu → **Settings → Secrets**.
3. Paste:

```toml
GEE_SERVICE_ACCOUNT_EMAIL = "soilsense-app@soilsense-demo.iam.gserviceaccount.com"
GEE_SERVICE_ACCOUNT_JSON = """
{
  "type": "service_account",
  "project_id": "soilsense-demo",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "soilsense-app@soilsense-demo.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
```

Paste the **full contents** of the JSON file between the triple quotes, including all the `\n` escape sequences inside the private key exactly as they appear.

4. Click **Save**. The app will restart automatically. The sidebar indicator for Earth Engine should turn green within a minute.

---

## Step 5 — Smoke-test the deployed app

Click through each tab and confirm:

- [ ] **Overview:** map loads, clicking different coordinates refreshes the scorecard
- [ ] **Soil health:** bar chart renders with six indicators
- [ ] **Soil health:** NDVI time series plot appears (confirms GEE is working)
- [ ] **Erosion:** factor decomposition table shows all five factors
- [ ] **Degradation risk:** probability and top drivers appear
- [ ] **Recommendations:** at least 3 cards render
- [ ] **Export:** both PDF and CSV downloads work

If NDVI is missing or empty, check the app logs (⋮ → **Manage app → Logs**) for errors from the `fetch_ndvi_timeseries` function.

---

## Step 6 — Optional polish

### Custom domain
Streamlit Cloud supports custom domains on the paid tier. On the free tier you'll use `your-app.streamlit.app`, which is fine for portfolio use.

### Screenshots for the README
Once deployed, take screenshots of each tab at 1600×1000 or similar, save them to `assets/screenshots/`, and add them to the README under the **Screenshots** heading. Annotate if helpful.

### Analytics
Add a simple counter if you want to track usage. Plausible or GoatCounter both work well with Streamlit via `st.components.v1.html`.

### Keep it awake
Free-tier apps sleep after 7 days of inactivity. A simple cron-based HTTP ping (GitHub Actions works) wakes it on a schedule. Don't abuse this — it's against the ToS to keep multiple apps artificially alive.

---

## Troubleshooting

**Build fails with `ERROR: Could not build wheels for rasterio`**
Streamlit Cloud has a recent GDAL — make sure `rasterio` and `rioxarray` versions in `requirements.txt` match what's on PyPI for the current Python runtime. If all else fails, try dropping `rioxarray` (the current `app.py` doesn't use it at runtime; it's listed for the training notebook).

**Earth Engine still shows offline after secrets are configured**
Check that you registered the service account at `signup.earthengine.google.com` (Step 3d). Also check app logs for the exact error — a 403 almost always means the service account isn't registered, and a 401 means the key is invalid.

**SoilGrids requests time out**
ISRIC occasionally rate-limits. The app caches aggressively (24 h TTL) so this is rare for users who've already loaded a location. If it persists, check [isric.org](https://www.isric.org) for status.

**App sleeps and takes 30s to wake**
Normal behavior on the free tier. The first user after inactivity will trigger a cold start.

---

## Beyond the free tier

If this becomes genuinely useful and sees real traffic, Streamlit Cloud has paid tiers, but at that point you'd likely want to move to a proper deployment — Cloud Run, Fly.io, or Azure App Service — with a real CDN in front. The app is a plain Streamlit container; no lock-in.
