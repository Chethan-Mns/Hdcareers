#!/usr/bin/env bash
# Exit 0 = skip Vercel build; exit 1 = deploy. Only state-only writes can skip.
set -euo pipefail
changes="$(git diff --name-only HEAD^ HEAD 2>/dev/null)" || exit 1
[ -n "$changes" ] || exit 1
while IFS= read -r file; do
  case "$file" in
    data/jobs.json|data/reel-selection.json|data/daily-review-batch.json|data/review-queue.json|data/vip-publish-request.json|data/approved-review-publication.json|data/telegram-deliveries.json|data/telegram-hourly-queue.json|data/telegram-approved-batch.json)
      ;;
    *)
      # Any website HTML, scripts, compiled styles, icons or job pages must deploy.
      exit 1
      ;;
  esac
done <<< "$changes"
echo "No public website assets changed; skipping redundant Vercel deployment."
exit 0
