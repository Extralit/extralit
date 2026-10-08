#!/usr/bin/env bash
# End-to-end demo build: seed -> record (asserting) -> transcode -> render.
#
# Deliberately fails closed. `record-demo.mjs` exits non-zero if any of its assertions fail,
# and `set -e` stops the pipeline there, so a broken /extractions UI can never be dressed up
# as a finished video.
#
# Requires the full stack up (server :6900, `npm run dev` :3000) and ffmpeg/ffprobe on PATH.
# See README.md.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$(dirname "$HERE")"

# Refuse up front rather than at the seed step. `seed_demo_workspace.py` still targets the
# /api/v2 routes the v1 fold deleted and exits 1 unconditionally, so this pipeline cannot
# succeed -- and without this guard it would first create (and, on a rerun, delete) the output
# directory before failing. Drop this block in the same change that repoints the seed.
cat >&2 <<'DISABLED'
run-demo.sh is disabled: demo/seed_demo_workspace.py has not been repointed at /api/v1
after the v2->v1 fold, so the pipeline cannot get past its first step.
See "Repointing demo/seed_demo_workspace.py" in
docs/superpowers/plans/2026-07-26-fold-followups.md.
DISABLED
exit 1
# Default outside the repo: recordings are large binaries and must never be committed.
OUT="${DEMO_OUT:-${TMPDIR:-/tmp}/extralit-extractions-demo}"

echo "==> output: $OUT"

# `DEMO_OUT` is a documented knob, and an unguarded `rm -rf "$OUT"` on it will happily wipe
# whatever the caller points at — `DEMO_OUT=$HOME`, `DEMO_OUT=$PWD`, or a path with a typo.
# Only ever recursively delete a directory this script created, identified by a marker file.
MARKER=".extralit-demo-out"
case "$OUT" in
  "" | "/" | "$HOME" | "$HOME/") echo "refusing to use '$OUT' as the demo output directory" >&2; exit 1 ;;
esac
if [ -e "$OUT" ]; then
  if [ ! -f "$OUT/$MARKER" ]; then
    echo "refusing to delete '$OUT': not a demo output directory (no $MARKER marker)." >&2
    echo "Remove it yourself, or point DEMO_OUT at a fresh path." >&2
    exit 1
  fi
  rm -rf "$OUT"
fi
mkdir -p "$OUT"
touch "$OUT/$MARKER"

echo "==> seeding demo workspaces"
uv run --project "$FRONTEND/../extralit-server" python "$HERE/seed_demo_workspace.py" \
  --output "$OUT/demo-seed.json"

# The extraction e2e seed supplies the second workspace the "switch workspace" scene swaps into.
if [ ! -f "$FRONTEND/e2e/extraction/seed/seed-output.json" ]; then
  echo "==> seeding the extraction e2e workspace (needed for the workspace-swap scene)"
  (cd "$FRONTEND" && npm run --silent e2e:extraction:seed)
fi

echo "==> recording (headless chromium, live backend)"
node "$HERE/record-demo.mjs" \
  --out "$OUT" \
  --seed "$OUT/demo-seed.json" \
  --e2e-seed "$FRONTEND/e2e/extraction/seed/seed-output.json"

echo "==> transcoding + generating the composition's data module"
node "$HERE/build-timeline.mjs" --out "$OUT"

echo "==> rendering"
cd "$HERE/video"
[ -d node_modules ] || npm install --no-audit --no-fund
npx remotion render ExtractionsDemo "$OUT/extractions-demo.mp4" --codec=h264 --crf=23

echo
echo "done: $OUT/extractions-demo.mp4"
