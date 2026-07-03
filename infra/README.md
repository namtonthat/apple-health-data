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

## Phone upload receiver (Lambda Function URL)

Health Auto Export POSTs each export to the `apple-health-ingest` Lambda's
Function URL (`infra/lambda/ingest_health_data.py`), which writes it to
`s3://<bucket>/landing/health/<utc-timestamp>.json` — the S3 event then fires
the refresh trigger below, so an upload refreshes the dashboard end to end.

- **`deploy-ingest-lambda.sh`** — idempotent deploy: IAM role (PutObject on
  `landing/health/*` only), function, and public Function URL. Requests must
  carry a shared token (`?token=…` or `x-api-key` header); the script prints
  the full URL to paste into the app and reuses the existing token on
  re-runs (`ROTATE_TOKEN=1` to mint a new one, then update the app).

## S3 event trigger (Lambda)

When a new Apple Health export JSON lands in
`s3://<bucket>/landing/health/`, the `apple-health-refresh-trigger` Lambda
(`lambda/trigger_refresh.py`) dispatches the `refresh-data.yml` workflow so
the dashboard refreshes immediately instead of waiting for the daily cron.

- **`deploy-trigger-lambda.sh`** — idempotent deploy: stores the GitHub PAT
  in SSM Parameter Store (`/apple-health-data/github-pat`), creates/updates
  the IAM role and Lambda, and wires the bucket notification
  (prefix `landing/health/`, suffix `.json`). Bucket and region are read
  from `pyproject.toml [tool.dashboard]`.

Prerequisites:

- Personal-account AWS credentials in the repo's `.env` (the script sources
  it and ignores any ambient `AWS_PROFILE`, then refuses to run unless the
  active account owns the bucket).
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
