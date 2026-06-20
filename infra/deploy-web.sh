#!/usr/bin/env bash
# deploy-web.sh — build the static web dashboard for publishing to GitHub Pages.
#
# Produces web/out/ (a fully static site). The GitHub Actions workflow
# (.github/workflows/deploy-web.yml) runs this, then uploads web/out as the
# Pages artifact. Run it locally too (`make web-build`) to preview the build.
#
# PAGES_BASE_PATH: set by CI to "/apple-health-data" so asset/route URLs are
# prefixed for the project-page subpath. Unset locally => builds for "/".
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

# Reproducible install: prefer the lockfile, fall back to a plain install.
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

npm run build

# GitHub Pages serves the artifact as-is (no Jekyll), but .nojekyll guarantees
# the _next/ directory is never stripped on any Pages configuration.
touch out/.nojekyll

echo "Built static site at $ROOT/web/out (base path: '${PAGES_BASE_PATH:-/}')"
