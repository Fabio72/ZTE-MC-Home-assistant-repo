#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/Kajkac/ZTE-MC-Home-assistant-repo.git}"
BRANCH="${BRANCH:-main}"

if ! git remote get-url upstream >/dev/null 2>&1; then
  git remote add upstream "$UPSTREAM_URL"
fi

git fetch upstream "$BRANCH"
git checkout "$BRANCH"

if git merge-base --is-ancestor "upstream/$BRANCH" HEAD && \
   [ "$(git rev-parse "upstream/$BRANCH")" = "$(git rev-parse HEAD)" ]; then
  echo "Branch $BRANCH is already aligned with upstream/$BRANCH."
  exit 0
fi

git merge "upstream/$BRANCH" --no-edit
git push origin "$BRANCH"

echo "Synced $BRANCH with upstream/$BRANCH and pushed to origin."
