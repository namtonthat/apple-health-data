# infra

Deployment infrastructure for the web dashboard (`../web`) and the S3 event
trigger Lambda. Kept free and all-in-repo: no servers, no paid hosting, no
extra accounts.

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

## S3 event trigger (Lambda)

When a new Apple Health export JSON lands in
`s3://<bucket>/landing/health/`, the `apple-health-refresh-trigger` Lambda
(`lambda/trigger_refresh.py`) dispatches the `refresh-data.yml` workflow so
the dashboard refreshes immediately instead of waiting for the daily cron.
See `docs/superpowers/specs/2026-07-03-s3-event-trigger-design.md` for the
full design.

- **`deploy-trigger-lambda.sh`** — idempotent deploy: stores the GitHub PAT
  in SSM Parameter Store (`/apple-health-data/github-pat`), creates/updates
  the IAM role and Lambda, and wires the bucket notification
  (prefix `landing/health/`, suffix `.json`). Bucket and region are read
  from `pyproject.toml [tool.dashboard]`.

Prerequisites:

- AWS credentials with IAM/Lambda/SSM/S3 access.
- A fine-grained GitHub PAT scoped to this repo with **Actions: read and
  write** permission.

Run (from repo root):

```bash
./infra/deploy-trigger-lambda.sh   # prompts for the PAT (hidden input)
```

Do **not** put the PAT inline on the command line (`GITHUB_PAT=... ./infra/...`)
— zsh writes the whole line, token included, to `~/.zsh_history`. For
non-interactive runs, read it into the environment without echoing it first:

```bash
read -rs GITHUB_PAT && export GITHUB_PAT
./infra/deploy-trigger-lambda.sh
```

Smoke test: upload any `.json` to `landing/health/`, then check
`gh run list --workflow refresh-data.yml` for a new run.

## Other free hosts

The same `web/out` works on Cloudflare Pages / Netlify (root domain, no
`PAGES_BASE_PATH` needed) if a cleaner URL or custom domain is wanted later.
