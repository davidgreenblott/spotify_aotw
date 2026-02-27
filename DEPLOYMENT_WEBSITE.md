# Website Deployment Guide — Netlify

The public-facing album website is a React + Vite app deployed on Netlify.
It auto-deploys whenever the bot pushes an updated `data.json` to the website GitHub repo.

---

## Architecture

```
Bot adds album
     │
     ▼
github_push.py  →  commits data.json to website repo
                         │
                         ▼
                   Netlify detects commit
                         │
                         ▼
                   npm run build  (Vite bundles site)
                         │
                         ▼
                   Site live in ~1 minute
```

---

## Netlify Setup

### 1. Create a separate GitHub repo for the website

The website lives in its own repo (separate from the bot). The bot pushes `data.json`
to this repo's root, triggering a Netlify rebuild.

Suggested structure of the website repo:
```
/
├── data.json          ← pushed here by the bot after each album add
├── src/
├── public/
├── index.html
├── package.json
├── vite.config.js
└── netlify.toml
```

### 2. Connect to Netlify

1. Go to [app.netlify.com](https://app.netlify.com) and log in
2. Click **Add new site → Import an existing project → GitHub**
3. Select the website repo
4. Netlify will detect `netlify.toml` automatically — no manual build settings needed
5. Click **Deploy site**

### 3. Update bot env vars

Once the website repo exists, set these in Railway:

| Variable | Value |
|---|---|
| `GITHUB_REPO_OWNER` | Your GitHub username |
| `GITHUB_REPO_NAME` | The website repo name (e.g. `aotw-website`) |
| `GITHUB_TOKEN` | Fine-grained PAT with **Contents: Read and Write** on the website repo |

---

## How data.json flows

1. Someone sends `@aotw <spotify_url>` in the Telegram group
2. Bot appends the album to the Google Sheet
3. Bot calls `export_and_push()` which:
   - Reads the full sheet and generates `data.json`
   - Commits and pushes it to the website repo root via GitHub API
4. Netlify detects the new commit and rebuilds
5. The site is live with the new album within ~1 minute

---

## Cache behaviour

Configured in `netlify.toml`:

| File | Cache |
|---|---|
| `data.json` | 5 minutes — stays fresh after each bot update |
| `assets/*.js` / `assets/*.css` | 1 year — safe because Vite adds content hashes to filenames |

---

## Manual deploy

If you need to force a redeploy without pushing a commit:

```bash
# Using Netlify CLI
npm install -g netlify-cli
cd website/
netlify deploy --prod
```

Or trigger it from the Netlify dashboard: **Deploys → Trigger deploy → Deploy site**.

---

## Local development

```bash
cd website/
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build → dist/
npm run preview   # preview production build locally
```
