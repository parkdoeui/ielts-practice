#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

WORKFLOW_FILE=".github/workflows/deploy-pages.yml"
WORKFLOW_NAME="Deploy Frontend to GitHub Pages"
POLL_SECONDS=5
MAX_POLLS=60

usage() {
  cat <<'EOF'
Usage:
  ./publish.sh "commit message"

What it does:
  1. Stages all current repo changes
  2. Creates a git commit with the provided message
  3. Pushes the current branch to origin
  4. Waits for the GitHub Pages workflow triggered by the push
  5. Verifies the live Pages site responds successfully

Notes:
  - Requires git, curl, and python3
  - Uses the public GitHub Actions API; no gh CLI required
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

COMMIT_MESSAGE="$1"

if [[ -z "$(git status --short)" ]]; then
  echo "No changes to publish."
  exit 0
fi

BRANCH="$(git branch --show-current)"
REMOTE_URL="$(git remote get-url origin)"
REMOTE_SLUG="$(printf '%s\n' "$REMOTE_URL" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
PAGES_URL="https://$(printf '%s' "$REMOTE_SLUG" | cut -d/ -f1).github.io/$(printf '%s' "$REMOTE_SLUG" | cut -d/ -f2)/"

echo "Staging changes..."
git add -A

echo "Creating commit..."
git commit -m "$COMMIT_MESSAGE"

HEAD_SHA="$(git rev-parse HEAD)"
PARENT_SHA="$(git rev-parse HEAD^ 2>/dev/null || true)"

echo "Pushing $BRANCH to origin..."
git push origin "$BRANCH"

echo "Waiting for Pages workflow: $WORKFLOW_NAME"

RUN_ID=""
for ((i=1; i<=MAX_POLLS; i++)); do
  RUN_ID="$(
    curl -fsSL "https://api.github.com/repos/$REMOTE_SLUG/actions/runs?head_sha=$HEAD_SHA" \
      | python3 -c 'import json,sys; data=json.load(sys.stdin); runs=data.get("workflow_runs", []); print(runs[0]["id"] if runs else "")'
  )"

  if [[ -n "$RUN_ID" ]]; then
    break
  fi

  sleep "$POLL_SECONDS"
done

if [[ -z "$RUN_ID" ]]; then
  echo "Could not find a workflow run for commit $HEAD_SHA."
  exit 1
fi

RUN_API_URL="https://api.github.com/repos/$REMOTE_SLUG/actions/runs/$RUN_ID"

for ((i=1; i<=MAX_POLLS; i++)); do
  RUN_STATE="$(
    curl -fsSL "$RUN_API_URL" \
      | python3 -c 'import json,sys; data=json.load(sys.stdin); print("{}:{}".format(data.get("status"), data.get("conclusion")))'
  )"

  echo "Workflow state: $RUN_STATE"

  if [[ "$RUN_STATE" == "completed:success" ]]; then
    break
  fi

  if [[ "$RUN_STATE" == completed:* && "$RUN_STATE" != "completed:success" ]]; then
    echo "Pages workflow did not succeed for $HEAD_SHA."
    exit 1
  fi

  sleep "$POLL_SECONDS"
done

FINAL_STATE="$(
  curl -fsSL "$RUN_API_URL" \
    | python3 -c 'import json,sys; data=json.load(sys.stdin); print("{}:{}".format(data.get("status"), data.get("conclusion")))'
)"

if [[ "$FINAL_STATE" != "completed:success" ]]; then
  echo "Timed out waiting for Pages workflow success."
  exit 1
fi

echo "Verifying live site: $PAGES_URL"
HTTP_STATUS="$(curl -L -s -o /dev/null -w '%{http_code}' "$PAGES_URL")"
if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "Live Pages site returned HTTP $HTTP_STATUS"
  exit 1
fi

INDEX_SNIPPET="$(curl -L -s "$PAGES_URL" | sed -n '1,20p')"
echo "Live Pages check passed."
echo "$INDEX_SNIPPET"
