# Skill: netlify-deploy

Deploy the static bookmark viewer to Netlify.

## Trigger

User says: "deploy to netlify", "redeploy", "push the static site", or similar.

## What this skill does

1. Reads `NETLIFY_AUTH_TOKEN` from `.env.local` (never from git)
2. Runs `xbm export-static` to regenerate all 7 output files in `data/static-export/`
3. Deploys to the linked Netlify site (`siteId` stored in `.netlify/state.json`)
4. Reports the production URL

## Site

- **URL:** https://xbm-viewer-export.netlify.app
- **Site ID:** 883d2359-e4e8-45bb-8ac1-c1b287abaf95 (stored in `.netlify/state.json`)

## Prerequisites

- `netlify` CLI installed (`brew install netlify-cli` or `npm install -g netlify-cli`)
- `.env.local` contains `NETLIFY_AUTH_TOKEN=<token>` (gitignored)
- Database has been synced (`xbm sync`) if you want fresh posts

## Steps for Claude to execute

```bash
# 1. Load token
source .env.local   # or: export $(grep -v '^#' .env.local | xargs)

# 2. Regenerate export
venv/bin/xbm export-static

# 3. Deploy
NETLIFY_AUTH_TOKEN=$NETLIFY_AUTH_TOKEN netlify deploy --dir data/static-export/ --prod
```

## Re-token

If the token expires or is revoked:
1. Go to https://app.netlify.com/user/applications#personal-access-tokens
2. Create a new token
3. Update `.env.local`: `NETLIFY_AUTH_TOKEN=<new-token>`


## Rich Embeds

Trigger: user says "deploy with rich embeds" or "redeploy with rich embeds"

Note: Twitter widget JS will be loaded from an external CDN at view time.

Command:
```bash
# 1. Load token
source .env.local

# 2. Regenerate export with native X widget HTML
venv/bin/xbm export-static --rich-embeds

# 3. Deploy
NETLIFY_AUTH_TOKEN=$NETLIFY_AUTH_TOKEN netlify deploy --dir data/static-export/ --prod
```

No confirmation prompt needed — CDN note above is informational only.
