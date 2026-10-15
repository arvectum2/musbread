#!/bin/zsh
# Safe, one-way fast-forward sync from GitHub to the Mac mini working tree.
set -euo pipefail
repo=/Volumes/ArvectumSSD/Arvectum/repos/musbread
test -d "$repo/.git" || exit 0
cd "$repo"
branch="$(git branch --show-current)"
if [[ "$branch" != main ]]; then
  echo "SKIP: active branch $branch"
  exit 0
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "SKIP: uncommitted changes"
  exit 0
fi
git fetch -q origin main
git merge --ff-only -q origin/main
echo "OK: $(git rev-parse --short HEAD)"
