#!/usr/bin/env bash
#
# push_to_github.sh
# ------------------
# Initializes this folder as a git repo (if it isn't already) and pushes
# the entire business_lead_finder structure to a GitHub repository.
#
# USAGE:
#   1. Create an empty repo on GitHub first (do NOT initialize it with a
#      README/.gitignore/license - this script will push everything).
#   2. From inside the business_lead_finder/ folder, run:
#
#        chmod +x push_to_github.sh
#        ./push_to_github.sh https://github.com/<your-username>/<your-repo>.git
#
#      or, for SSH:
#
#        ./push_to_github.sh git@github.com:<your-username>/<your-repo>.git
#
#   Optional: pass a branch name as the 2nd argument (default: main)
#   and a commit message as the 3rd argument.
#
#   If you use HTTPS and 2FA, GitHub will prompt for a Personal Access
#   Token (not your password) - create one at:
#   https://github.com/settings/tokens

set -euo pipefail

REMOTE_URL="${1:-}"
BRANCH="${2:-main}"
COMMIT_MSG="${3:-Initial commit: Business Lead Finder}"

if [ -z "$REMOTE_URL" ]; then
  echo "Usage: ./push_to_github.sh <repo-url> [branch] [commit-message]"
  echo "Example: ./push_to_github.sh https://github.com/yourname/business-lead-finder.git"
  exit 1
fi

# Make sure we're running from the project root (where this script lives)
cd "$(dirname "$0")"

if [ ! -d ".git" ]; then
  echo "==> Initializing new git repository..."
  git init
  git branch -M "$BRANCH"
else
  echo "==> Existing git repository detected, reusing it."
fi

# Make sure .env is never committed even if the user removed .gitignore's entry
if [ -f ".env" ] && ! grep -qxF ".env" .gitignore 2>/dev/null; then
  echo ".env" >> .gitignore
fi

echo "==> Staging files..."
git add .

if git diff --cached --quiet; then
  echo "==> Nothing new to commit."
else
  echo "==> Committing..."
  git commit -m "$COMMIT_MSG"
fi

echo "==> Setting remote 'origin' to $REMOTE_URL"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "==> Pushing to $REMOTE_URL ($BRANCH)..."
git push -u origin "$BRANCH"

echo "==> Done. Repository pushed successfully."
