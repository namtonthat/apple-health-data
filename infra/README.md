# infra

Deployment infrastructure for the web dashboard (`../web`). Kept free and
all-in-repo: no servers, no paid hosting, no extra accounts.

## How it works

The dashboard is a **static export** (`next build` with `output: "export"` →
`web/out/`), published to **GitHub Pages** (free for this public repo).

```
push to main (web/** or data) ──▶ .github/workflows/deploy-web.yml
                                     └─ infra/deploy-web.sh   (npm ci + build → web/out)
                                     └─ actions/deploy-pages  (publish web/out)
                                          └─▶ https://namtonthat.github.io/apple-health-data/
```

- **`deploy-web.sh`** — builds `web/out`. Used by CI and by `make web-build`.
- **`.github/workflows/deploy-web.yml`** — builds + deploys on every push that
  touches `web/**` (including the daily `chore: refresh dashboard data` commit,
  so the site self-updates), or on manual dispatch.
- `PAGES_BASE_PATH=/apple-health-data` (set in the workflow) prefixes asset and
  route URLs for the project-page subpath. Local builds leave it unset → `/`.

## One-time setup

GitHub Pages must be set to **Build and deployment → Source: GitHub Actions**
(repo Settings → Pages). The `configure-pages` action enables this on first run;
if the first deploy fails, set it manually once.

## Commands (from repo root)

```bash
make web-build    # build the static site locally into web/out
make deploy-web   # trigger the GitHub Pages deploy workflow (gh CLI)
```

A normal `git push` that changes `web/**` also deploys automatically.

## Other free hosts

The same `web/out` works on Cloudflare Pages / Netlify (root domain, no
`PAGES_BASE_PATH` needed) if a cleaner URL or custom domain is wanted later.
