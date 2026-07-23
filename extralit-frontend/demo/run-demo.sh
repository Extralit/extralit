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
# Default outside the repo: recordings are large binaries and must never be committed.
OUT="${DEMO_OUT:-${TMPDIR:-/tmp}/extralit-extractions-demo}"

echo "==> output: $OUT"
rm -rf "$OUT"
mkdir -p "$OUT"

echo "==> seeding demo workspaces"
uv run --project "$FRONTEND/../extralit-server" python "$HERE/seed_demo_workspace.py" \
  --output "$OUT/demo-seed.json"

# The v2 e2e seed supplies the second workspace the "switch workspace" scene swaps into.
if [ ! -f "$FRONTEND/e2e/v2/seed/seed-output.json" ]; then
  echo "==> seeding the v2 e2e workspace (needed for the workspace-swap scene)"
  (cd "$FRONTEND" && npm run --silent e2e:v2:seed)
fi

echo "==> recording (headless chromium, live backend)"
node "$HERE/record-demo.mjs" \
  --out "$OUT" \
  --seed "$OUT/demo-seed.json" \
  --e2e-seed "$FRONTEND/e2e/v2/seed/seed-output.json"

echo "==> transcoding + generating the composition's data module"
node "$HERE/build-timeline.mjs" --out "$OUT"

echo "==> rendering"
cd "$HERE/video"
[ -d node_modules ] || npm install --no-audit --no-fund
npx remotion render ExtractionsDemo "$OUT/extractions-demo.mp4" --codec=h264 --crf=23

echo
echo "done: $OUT/extractions-demo.mp4"
