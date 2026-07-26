# `/extractions` demo video harness

Records the workspace-wide extraction grid driving a **live** backend in headless Chromium,
then composes the recording into an annotated 1080p video with [Remotion](https://remotion.dev).

It is a demo **and** a gate. Every scene asserts the behaviour it is showing; a failed
assertion exits non-zero and stops the pipeline, so a broken UI can't be dressed up as a
finished video. The composition renders the real pass/fail counts, so the video is a report
on the run rather than a hand-authored claim about it.

## Run it

Needs the full stack up — server on `:6900`, `npm run dev` on `:3000` — plus `ffmpeg` and
`ffprobe` on `PATH`. See the root `CLAUDE.md` for stack setup.

```bash
./demo/run-demo.sh
```

Output defaults to `$TMPDIR/extralit-extractions-demo/` (**outside the repo** — recordings and
renders are large binaries and must never be committed). Override with `DEMO_OUT=...`.

Artifacts:

| file | what |
|---|---|
| `extractions-demo.mp4` | the finished 1080p video |
| `timeline.json` | scene boundaries + every assertion's pass/fail |
| `shots/*.png` | one full-page screenshot per scene |
| `console.log` | browser console + `pageerror` capture |
| `video/*.webm` | the raw headless recording |

## Pieces

| file | role |
|---|---|
| `seed_demo_workspace.py` | builds the `malaria-demo` + `empty-demo` workspaces |
| `record-demo.mjs` | drives + asserts + records; writes `timeline.json` |
| `build-timeline.mjs` | webm→CFR-mp4 transcode, generates `video/src/data.ts` |
| `video/` | the Remotion composition (isolated React 19 sub-package) |

`video/` is a **separate npm package on purpose**: Remotion pulls React 19 and its own
toolchain, none of which belong in the Nuxt app's dependency graph. It is also excluded from
the app's ESLint config. `npm install` there is on demand — `run-demo.sh` does it if needed.

`video/src/data.ts` is **generated, never committed**. The composition is a report on one
specific run; committing it would let stale captions render against a fresh recording.

## What the seed is shaped to prove

`e2e/v2/seed/seed_v2_e2e.py` is a minimal assertion fixture. This one is a realistic
systematic review, shaped so every grid affordance has something to show:

- **`study_characteristics`** — scalar questions with scored agent suggestions.
- **`outcomes`** — a `table` question (arm / n / incidence) that fans one reference out to
  several stacked rows, which is what makes reference-group banding visible.
- **`risk_of_bias`** — questions but *zero* records: its columns still appear, empty. This is
  the coverage map, and it's the whole point of a workspace-wide projection.
- One reference where a human submitted `cluster-RCT` over the agent's `cohort`, so
  response-beats-suggestion coalescing is observable rather than asserted in the abstract.
- Deliberate holes (a missing country, a missing sample size, a reference with no outcomes
  record) so absent extractions render blank instead of being fabricated.

## Gotchas

- **Perspective renders into a shadow root.** `document.querySelectorAll("td")` finds nothing;
  the driver's `GRID_PROBE` walks every open shadow root instead.
- **Perspective infers numeric columns.** A digit-only value like `4812` renders as `4,812`,
  so assertions compare against a separator-stripped copy.
- **npm blocks esbuild's postinstall.** `video/package.json` carries an `allowScripts` entry
  for it; without that the Remotion bundler fails at render time.
- **Headless Chromium paints no cursor.** The driver injects one so clicks and scrolls read on
  screen, and hides the Nuxt devtools anchor (dev-server furniture, not the feature).
