---
description: Step-by-step guide for creating a new Extralit release
hide:
 - footer
---

# Extralit Release Guide

Releasing Extralit is one workflow dispatch. You do not create branches, edit version files, push tags, or draft release notes by hand — `release.yml` does all of it, and refuses to run if the state isn't right.

## Cut a release

```sh
# 1. Rehearse. Validates everything and prints a plan, but pushes nothing.
gh workflow run release.yml -f version=0.7.0

# 2. Read the plan in the run summary, then cut it for real.
gh workflow run release.yml -f version=0.7.0 -f dry_run=false
```

`dry_run` defaults to **true**, so the first command is the safe default and a bare `gh workflow run release.yml -f version=…` can never publish anything. Watch either run with `gh run watch`.

The plan table in the run summary tells you the version, the tag, the exact commit on `main` being released, whether the release is already converged, and whether the run is in `DRY RUN` or `EXECUTE` mode. Read it before step 2.

You can also run both from the **Actions → Release** page if you prefer the UI.

## What happens automatically

Once `dry_run=false` succeeds, one commit stamping the version lands on `main`, `release`, and the tag `v0.7.0` — all three at the same SHA, pushed atomically. That single push then drives everything else in parallel:

| Trigger | Result |
| --- | --- |
| `release` build (dispatched by `release.yml`, not by the push — see below) | multi-arch `extralit/extralit-server:v0.7.0` + `:latest`, then the HF Space rebuild that restarts **`extralit/public-demo`** |
| push to tag `v0.7.0` | `extralit` and `extralit-server` published to PyPI |
| push to tag `v0.7.0` | versioned docs at `docs.extralit.ai/v0.7/`, with `stable` re-pointed at it |
| push to tag `v0.7.0` | a GitHub Release with notes generated from merged PR titles |

The GitHub Release step waits until PyPI actually serves both packages before publishing, so a release is never announced before it's installable.

The production build is the one row above that is *not* driven by the atomic push. `release.yml` dispatches it explicitly, because GitHub matches a workflow's `paths:` filter against the diff a push carries — and when `release` is created at a commit that already exists on `main`, that push carries no changed files and starts nothing. Cutting `v0.7.0` hit exactly that: `main` and the tag both built, `release` built nothing, and the production image had to be triggered by hand.

## Verify

```sh
git ls-remote origin refs/heads/main refs/heads/release refs/tags/v0.7.0   # all three at one SHA
pip index versions extralit
curl -s https://extralit-public-demo.hf.space/api/v1/status | jq .version  # 0.7.0
gh release view v0.7.0
```

Docs land at [docs.extralit.ai/v0.7/](https://docs.extralit.ai/v0.7/), and `stable` should redirect there.

## If something goes wrong

The workflow reports exactly which precondition failed.

**"Tag v0.7.0 already exists at a different commit."** A previous attempt got partway. If that tag is genuinely wrong, delete it and re-run:

```sh
git push origin :refs/tags/v0.7.0 && git tag -d v0.7.0
```

If the tag is correct and already points at a commit stamped `0.7.0`, the workflow instead reports **`Converged already: true`** and does nothing. Re-running a completed release is always safe — that's the property that makes recovery possible.

**"CI is not green on `main`."** The workflow refuses to release an untested commit and tells you whether checks are failing, still running, or absent entirely. Wait for them, or override deliberately:

```sh
gh workflow run release.yml -f version=0.7.0 -f dry_run=false -f skip_ci_check=true
```

**"Not authorized."** Cutting a release requires `admin` or `maintain` on the repository.

## Roll back

Production follows the `release` branch, so rolling back means moving it and restarting the Space — no revert commit, no new version:

```sh
git push --force-with-lease origin v0.6.1^{commit}:refs/heads/release
```

That rebuilds and redeploys `extralit/public-demo` from the previous release. PyPI releases cannot be un-published — if a bad version reached PyPI, yank it there and cut a fixed patch release instead.

## Announce

Share the generated release notes with the community (Slack, GitHub Discussions).
