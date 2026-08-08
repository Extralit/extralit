# Deployment & CI/CD Architecture

How a code change in any monorepo module flows through GitHub Actions to the
public demo at **<https://extralit-public-demo.hf.space>**.

This document traces the end-to-end pipeline that turns a commit into a running
Hugging Face Space. The terminal step is
[`extralit-hf-space/.github/workflows/build-hf-space.yml`](../../extralit-hf-space/.github/workflows/build-hf-space.yml),
which lives in the **separate** `extralit/extralit-hf-space` repository (vendored
here as a git submodule).

---

## 0. Branching model

Extralit is **trunk-based**. There is no `develop` branch and no `releases/**`
branches.

| Ref | Role | Images | Deploys to |
| --- | --- | --- | --- |
| `main` | trunk, default branch; every merged PR | `extralitdev/*:main` + `:latest`, amd64 | `extralit-dev/develop` |
| `release` | long-lived production pointer | `extralit/*:vX.Y.Z` + `:latest`, amd64+arm64 | `extralit/public-demo` |
| `vX.Y.Z` tag | the release itself | — | PyPI, versioned docs, GitHub Release |
| PR (`N/merge`) | preview | `extralitdev/*:pr-N`, amd64 | ephemeral `extralit-dev/pr-N` |

`release` is always a tagged point on `main`'s history: the release workflow
pushes one version-stamp commit to `main`, `release`, and the tag **atomically**,
so all three land at the same SHA. Nothing else ever writes to `release`, and
production only moves when [`release.yml`](../../.github/workflows/release.yml)
is deliberately dispatched. See
[`extralit/docs/community/release_guide.md`](../../extralit/docs/community/release_guide.md).

**`is_release` is the only production signal.** Branch names are not load-bearing
in the deploy path — the HF Space repo routes on the dispatch payload's
`is_release` flag, so a payload without it can never reach production whatever
branch it names.

---

## 1. The big picture

The pipeline spans **two repositories** and is glued together by a GitHub
`repository_dispatch` event:

```mermaid
flowchart TD
    subgraph monorepo["Repo: extralit/extralit (monorepo)"]
        push["push to main / release"]
        rel[".github/workflows/release.yml (manual dispatch)"]
        prready["PR ready_for_review / manual dispatch"]
        fe[".github/workflows/extralit-frontend.yml"]
        sdk[".github/workflows/extralit.yml"]
        srv[".github/workflows/extralit-server.yml"]
        prev[".github/workflows/extralit-frontend.build-push-dev.yml"]
        srvbuild["extralit-server.build-docker-images.yml"]
    end

    subgraph hub["Docker Hub"]
        srvimg["extralit(dev)/extralit-server:&lt;tag&gt;"]
        spaceimg["extralit(dev)/extralit-hf-space:&lt;tag&gt;"]
    end

    subgraph hfrepo["Repo: extralit/extralit-hf-space"]
        bhs["build-hf-space.yml"]
    end

    subgraph hf["Hugging Face"]
        demo["Space: extralit-public-demo.hf.space"]
        dev["Space: extralit-dev-develop.hf.space"]
        prspace["PR preview Space: extralit-dev/pr-N"]
    end

    rel -->|"atomic push: main + release + tag"| push
    push --> fe
    push --> sdk
    push --> srv
    prready -->|server OR frontend PR| prev
    fe -->|SPA artifact| srv
    srv -->|tests + downloads SPA + wheel| srvbuild
    prev -->|downloads SPA + wheel| srvbuild
    srvbuild -->|build & push| srvimg
    srvbuild -->|repository_dispatch: build-hf-space| bhs
    bhs -->|FROM server image + ES/Redis/OCR| spaceimg
    bhs -->|"commit digest pin (is_release=true)"| demo
    bhs -->|"commit digest pin (branch=main)"| dev
    bhs -->|duplicate + retarget| prspace
```

**Key insight:** the HF Space image is built **`FROM` the `extralit-server`
image**, and the server image bundles a **prebuilt frontend SPA** as its fallback
UI. So the demo is rebuilt by whichever workflow rebuilds that server image: the
**`extralit-server`** workflow drives `main` and `release`, and
**`extralit-frontend.build-push-dev.yml`** drives per-PR ephemeral Spaces (it
rebuilds the same server image — SPA baked in — so frontend-only PRs get a
preview too). Both hand off to the same `build-docker-images.yml` +
`repository_dispatch`. See [§6 Gotchas](#6-gotchas--operational-notes).

---

## 2. Module → workflow routing

Each module has its own workflow, gated by `paths:` filters so unrelated changes
don't trigger unrelated builds. All three run on **push to `main`/`release`** and
on **`pull_request`**.

| Module (dir)        | Workflow                          | Triggers on path                              | Produces                                            | Reaches the demo? |
| ------------------- | --------------------------------- | --------------------------------------------- | --------------------------------------------------- | ----------------- |
| `extralit-server/`  | `extralit-server.yml`             | `extralit-server/**` (push/PR)                | `extralit-server` Docker image + PyPI wheel         | **Yes** (`main` → dev Space; `release` → public demo) |
| `extralit-frontend/`| `extralit-frontend.yml`           | `extralit-frontend/**`                        | Prerendered SPA artifact (plus tests/lint)          | Indirect¹         |
| *(server **or** frontend PR)* | `extralit-frontend.build-push-dev.yml` | **Non-fork** PR `ready_for_review` on `extralit-server/**` **or** `extralit-frontend/**`; or manual `pr_number` (works for forks too) | `extralitdev/extralit-server:pr-N` image → ephemeral Space | **Yes** (`extralit-dev/pr-N`) |
| `extralit/` (SDK)   | `extralit.yml`                    | `extralit/**` (excl. `docs/`, `mkdocs.yml`)   | `extralit` PyPI wheel                               | No²               |
| `extralit/docs/`    | `extralit.docs.yml`               | `extralit/docs/**`, `mkdocs.yml`              | Versioned docs via `mike` → `gh-pages`              | No                |
| *(whole repo)*      | `release.yml`                     | manual dispatch only                          | version stamp on `main` + `release` + `vX.Y.Z` tag  | **Yes** (indirectly) |
| *(none)*            | `github-release.yml`              | `vX.Y.Z` tag                                  | GitHub Release, once PyPI serves both packages      | No³ |
| `extralit-hf-space/`| `build-hf-space.yml` *(other repo)* | repository_dispatch / manual                | `extralit-hf-space` Docker image + Space deploy | **Yes** (terminal) |

¹ The frontend's own workflow tests, lints, and uploads a prerendered SPA
artifact; the **live** UI is deployed separately by Vercel's native Git
integration (configured in `extralit-frontend/vercel.ts`, not by any workflow).
The SPA the *server* ships is downloaded from this workflow's artifact (see §3).
A frontend-only change does not redeploy the public demo on its own — that needs
a release — but a frontend-only **PR** *does* get an ephemeral preview (see §3a).

² The SDK is published to PyPI and is *consumed by* the demo's CI for
integration tests (it spins up `extralitdev/extralit-hf-space:latest` as a
service container), but SDK changes never rebuild the Space image.

³ [`github-release.yml`](../../.github/workflows/github-release.yml) runs **zero
project code** — no checkout, no install, no build. It holds `contents: write`
and fires on a tag, so a malicious tagged commit must have nothing there to
execute. It polls PyPI for both packages first and only then runs `gh release
create --verify-tag --generate-notes`, so a release is never announced before it
is installable and `gh` can never mint a tag of its own. Note headings come from
PR **labels** via [`.github/release.yml`](../../.github/release.yml) — the
`feat:`/`fix:` title convention is for humans and is not what GitHub reads.

---

## 3. Stage A — `extralit-server.yml` (in the monorepo)

File: [`.github/workflows/extralit-server.yml`](../../.github/workflows/extralit-server.yml)

Triggered by push to `main`/`release`, by pull requests, or manually
(`workflow_dispatch`).

### Job `build`
1. Spins up service containers (Elasticsearch, Postgres, Redis, MinIO) and runs
   `pytest tests/unit` with coverage → Codecov.
2. **Downloads the prebuilt frontend SPA** via the
   [`download-frontend-artifact`](../../.github/actions/download-frontend-artifact)
   composite action, which fetches the latest successful `extralit-frontend.yml`
   artifact for `main` — **always `main`**, release builds included, because the
   action needs a *previously successful* run on the branch it names and `release`
   only ever carries a commit that already landed on `main`. The server does
   **not** run `npm`.
3. Copies `extralit-frontend/.output/public` into `src/extralit_server/static`,
   asserts `index.html` exists, then `uv build` → uploads the `extralit-server`
   wheel artifact.

> **Why prebuilt, and why `BASE_URL=/`.** Since the Nuxt 4 migration the SPA is
> prerendered by `nuxi generate` at `BASE_URL=/` and shipped as static files; the
> old Nuxt 2 `@@baseUrl@@` placeholder breaks Nuxt 4's prerender crawler.
> Parameterizable sub-path hosting is a separate follow-up. The SPA is otherwise
> env-agnostic (it calls a relative `/api`), so one artifact works wherever the
> server is deployed.

### Job `build_docker_images` → `extralit-server.build-docker-images.yml`
File: [`.github/workflows/extralit-server.build-docker-images.yml`](../../.github/workflows/extralit-server.build-docker-images.yml)

Runs on branch pushes (`main` / `release`) and `workflow_dispatch` only —
`github.ref_type == 'branch' && github.event_name != 'pull_request'`. **PRs run
tests and nothing else here;** their preview images come from
`extralit-frontend.build-push-dev.yml` (§3a), which is the only caller that
passes `pr_number`. Tag pushes are excluded too: the image is already built from
`release` at the same SHA, and a tag-triggered build would dispatch
`branch=vX.Y.Z`, which `resolve-env` would turn into a junk preview Space.

The `release` build is started by an explicit `workflow_dispatch` from
`release.yml`, **not** by the `release` push event. GitHub matches a workflow's
`paths:` filter against the diff a push carries, and on the first release
`refs/heads/release` is created at a commit that already exists on `main` — that
push carries no changed files, so every paths-filtered workflow silently skips
it. Dispatching removes the dependency on push semantics entirely; if the push
event does also fire, the shared `${{ github.workflow }}-${{ github.ref }}`
concurrency group cancels the duplicate.

| Input                  | `is_release` (`release` branch) | dev (`main` / PR)               |
| ---------------------- | ------------------------------- | ------------------------------- |
| Docker org             | `extralit/extralit-server`      | `extralitdev/extralit-server`   |
| Platforms              | `linux/amd64,linux/arm64`       | `linux/amd64`                   |
| Image tag              | `v<package_version>`            | branch name (cleaned) or `pr-N` |
| Publish `:latest`      | only on `release`               | dev `:latest`, except PR previews (`pr_number` set) |

The version comes from
[`scripts/bump_version.py check`](../../scripts/bump_version.py), the single
owner of the three files that carry it. The dev tag is derived by the
[`docker-image-tag-from-ref`](../../.github/actions/docker-image-tag-from-ref)
composite action: tags → `<tag>`, PRs → `pr-<number>`, branches → `<branch>` with
non-alphanumerics replaced by `-`.

After building & pushing the server image, the final step fires the
cross-repo trigger:

```yaml
- name: Trigger HF-Space build
  uses: peter-evans/repository-dispatch@v3
  with:
    token: ${{ secrets.GH_ACTIONS_REPOSITORY_DISPATCH }}
    repository: extralit/extralit-hf-space
    event-type: build-hf-space
    client-payload: '{"tag":"${{ env.IMAGE_TAG }}","is_release":${{ inputs.is_release }},"branch":"${{ env.DISPATCH_BRANCH }}"}'
```

This hands off control — with `tag`, `is_release`, and `branch` — to the HF Space
repo. `DISPATCH_BRANCH` is `github.ref_name` normally, or `<n>/merge` when the
reusable build is called with the optional `pr_number` input (manual PR preview),
so `resolve-env` routes to `pr_space_slug=pr-N`.

> The `publish_release` job publishes the `extralit-server` wheel to (Test)PyPI,
> and fires **only on a `vX.Y.Z` tag push** — not on branch pushes. Under
> trunk-based development a branch-gated publish would try to release on every
> merge to `main`. Not part of the Space deploy.

---

## 3a. PR preview — `extralit-frontend.build-push-dev.yml` (in the monorepo)

File: [`.github/workflows/extralit-frontend.build-push-dev.yml`](../../.github/workflows/extralit-frontend.build-push-dev.yml)
(its `name:` is **"Deploy PR preview HF Space"**)

A single-purpose workflow that gives a server- **or** frontend-touching PR from a
branch **in this repository** an ephemeral Space, deliberately decoupled from
`extralit-server.yml` so it does **not** run on every push:

- **Auto:** `pull_request: types: [ready_for_review]` on `extralit-server/**` or
  `extralit-frontend/**`. Marking a PR ready (not each subsequent push) builds the
  preview; refresh later via the manual path. (`ready_for_review` only fires on a
  draft→ready transition — a PR opened directly as non-draft won't auto-trigger;
  re-mark it ready or use the manual path.)
- **Manual:** `workflow_dispatch` with a `pr_number` input — (re)deploy a chosen PR
  on demand, resolving `refs/pull/<n>/merge` so the run is self-contained.

> **Fork PRs get no automatic preview.** Both guarded jobs carry
> `github.event.pull_request.head.repo.fork == false` (`build` at :43,
> `point-preview-at-pr-space` at :110; `build_docker_images` is skipped
> transitively via `needs`), because a fork PR receives no repository secrets —
> the Docker login and cross-repo dispatch would fail. A maintainer *can* still
> produce one: the **manual** path resolves `refs/pull/<n>/merge`, which exists for
> fork PRs, and runs in this repo's context with secrets. Review a fork PR's code
> before dispatching — the preview builds that PR's merge ref.

Its `build` job downloads the prebuilt SPA and builds the wheel (no pytest), then
calls the same [`build-docker-images.yml`](../../.github/workflows/extralit-server.build-docker-images.yml)
with `is_release: false` and `pr_number`. Result: `extralitdev/extralit-server:pr-N`
is pushed and the dispatch (`branch=<n>/merge`) drives the HF Space repo's
`deploy-pr-space` job → **`extralit-dev/pr-N`** (`extralit-dev-pr-N.hf.space`).
`main`/`release` deploys are untouched and still flow through §3.

A third job, `point-preview-at-pr-space`, best-effort points the PR's **Vercel**
preview at that PR's own Space by setting a branch-scoped `API_BASE_URL` preview
env var and redeploying. It never blocks the pipeline.

---

## 4. Stage B — `build-hf-space.yml` (in `extralit/extralit-hf-space`)

File: [`extralit-hf-space/.github/workflows/build-hf-space.yml`](../../extralit-hf-space/.github/workflows/build-hf-space.yml)

Entry points:
- **`repository_dispatch` / `build-hf-space`** — the automated path from Stage A.
- **`workflow_dispatch`** — manual rebuild of the current ref. Carries no
  payload, so it always resolves to `staging`; a manual run **cannot** reach
  production.

### Job `resolve-env`
Pure-bash step that maps the dispatch payload to build parameters. It branches on
`is_release` **first**; branch names only distinguish trunk from preview:

| Payload                               | `env_name`   | `image_tag`          | `tag_latest` | `platforms`   | `pr_space_slug` |
| ------------------------------------- | ------------ | -------------------- | ------------ | ------------- | --------------- |
| `is_release=true`                     | `production` | payload `tag` (`v…`) | `true`       | `amd64,arm64` | — (empty)       |
| `branch=main` (or `develop`†)         | `staging`    | payload `tag`        | `true`       | `amd64`       | — (empty)       |
| any other branch (PR merge ref)       | `staging`    | payload `tag`        | `false`      | `amd64`       | `pr-N` / slug   |
| `workflow_dispatch`                   | `staging`    | `latest`             | per ref      | `amd64`       | per ref         |

† `develop` is a **migration alias** kept so dispatches still in flight from the
pre-trunk monorepo land on staging instead of spinning up a stray preview Space.
Remove it once the trunk flip has been verified.

`env_name` selects the GitHub **Environment** (`production` vs `staging`), which
is how per-environment secrets/vars are scoped: `DOCKER_REPO`,
`EXTRALIT_SERVER_IMAGE`, `HF_SPACE_ID`,
`DOCKER_USERNAME`/`DOCKER_PASSWORD` (plus `HF_TOKEN` on `staging`, which only
`deploy-pr-space` still uses — see §4).

Note the environments carry **no protection rules and no branch policy**, so
`environment:` here is a scoping mechanism, not an approval gate. What actually
confines production access is the per-job `permissions:` block (§3).

### Job `build`
Builds the self-contained Space image **on top of the server image**:

```yaml
build-args: |
  EXTRALIT_SERVER_IMAGE=${{ vars.EXTRALIT_SERVER_IMAGE }}
  EXTRALIT_VERSION=${{ needs.resolve-env.outputs.image_tag }}
```

The [`Dockerfile`](../../extralit-hf-space/Dockerfile) does
`FROM ${EXTRALIT_SERVER_IMAGE}:${EXTRALIT_VERSION}` and layers on **Elasticsearch
8.17**, **Redis**, the **OCR/PDF-extraction** package, and a Procfile-based
multi-process runtime (elastic + redis + RQ workers + FastAPI). Pushed to
`extralit/extralit-hf-space` (production) or `extralitdev/extralit-hf-space`
(staging), tagging `:latest` when `tag_latest=true`.

### Job `deploy-space` — *non-PR builds only* (`pr_space_slug == ''`)
Deploys by **committing to the Space repo**, not by restarting it. The Space is a
thin `FROM <pushed image>` Dockerfile; the job rewrites that `FROM` line to the
**digest** `build` just pushed and commits it, and HF rebuilds on the new commit.

```yaml
permissions:
  contents: read
  id-token: write          # mint the OIDC token; see below
env:
  HF_OIDC_RESOURCE: spaces/${{ vars.HF_SPACE_ID }}
  IMAGE_DIGEST: ${{ needs.build.outputs.image_digest }}
```
```python
after = re.sub(r"^FROM\s+\S+", f"FROM {repo}@{digest}", before, count=1, flags=re.M)
api.upload_file(path_or_fileobj=after.encode(), path_in_repo="Dockerfile",
                repo_id=space, repo_type="space", commit_message=f"Deploy {pin}")
```

**Why a commit and not `restart_space()`.** The restart API answers **401** to an
OIDC token: a repo publisher grants *write access to that repo*, and restarting is
a runtime operation rather than a repo write. Committing is what the credential is
for, and is HF's own
[documented GitHub Actions pattern](https://huggingface.co/docs/hub/en/spaces-github-actions).
A 401 here is specifically the restart endpoint — a misconfigured publisher fails
earlier and differently, as `OIDCError`/`invalid_grant` from the exchange.

**Why a digest and not a tag.** When the `FROM` line was `:latest`, HF reused the
base image it had already built and never re-pulled — the job went green while the
Space served the old build. That is the v0.7.0 failure: it cycled
`RUNNING_APP_STARTING → RUNNING` and still reported 0.6.1. A digest cannot resolve
to a previously-built image, which retires the `factory_reboot=True` workaround
that used to paper over this.

Re-deploying an unchanged digest is a no-op commit and so triggers no rebuild; that
path skips the wait and asserts the Space's *current* stage is `RUNNING`, so an
earlier failed build is never reported as a green redeploy.

**This job holds no HF credential.** It authenticates with
[Trusted Publishers](https://huggingface.co/docs/hub/en/trusted-publishers):
GitHub Actions mints a short-lived OIDC id token, and HF exchanges it (RFC 8693)
for a token scoped to that one Space for ~1h. `huggingface_hub` does the whole
dance inside `get_token()` when `HF_OIDC_RESOURCE` is set, and raises `OIDCError`
rather than falling back to an ambient credential.

Each Space registers a publisher pinned to repo `Extralit/extralit-hf-space`,
branch `main`, workflow `build-hf-space.yml`. Those claims are satisfied by
*every* job in this file, so the `id-token: write` grant is deliberately scoped to
this job alone — `build` and `deploy-pr-space` inherit only the workflow-level
`contents: read` and therefore cannot mint a token to exchange at all.

`HF_SPACE_ID` is the environment-scoped Space (see §5): the **`production`**
environment points at `extralit/public-demo` — the live public demo served at
**<https://extralit-public-demo.hf.space>** — while the **`staging`**
environment points at `extralit-dev/develop`
(`extralit-dev-develop.hf.space`).

### Job `deploy-pr-space` — *PR builds only* (`pr_space_slug != ''`)
Runs under `environment: staging`. Creates an ephemeral preview Space per PR:
1. `duplicate_space("extralit-dev/develop" → "extralit-dev/pr-N")` (cpu-basic) on
   first run, writing a README that enables `app_port: 6900`.
2. **Propagates config.** `duplicate_space` copies files but **not** secrets/variables,
   so the job forwards the `staging` GitHub environment's `EXTRALIT_*` onto the Space —
   env **secrets** → `add_space_secret`, env **variables** → `add_space_variable`. It
   strictly filters to the `EXTRALIT_` prefix (via `toJSON(secrets)`/`toJSON(vars)`), so
   `HF_TOKEN`/`DOCKER_*`/the GitHub token are never pushed; only keys are logged.
3. Uploads a one-line `Dockerfile` (`FROM extralitdev/extralit-hf-space:pr-N`) so
   the preview Space tracks the PR's image.

> **The Space `extralit-dev/develop` keeps its name.** It is a Hugging Face
> resource, not a git branch. The custom OAuth app is pinned to its
> `extralit-dev-develop.hf.space` callback, so renaming it breaks sign-in. This is
> the one place the word "develop" legitimately survives the trunk migration.

> **OAuth is not wired for previews.** That same pinning means ephemeral `pr-N`
> domains can't serve the callback, so sign-in won't work on a preview. Do **not**
> put `EXTRALIT_ELASTICSEARCH`/`EXTRALIT_REDIS_URL` in the `staging` env — the
> bundle runs its own ES/Redis at `localhost` and the generic filter would
> otherwise override them.

---

## 5. Environment & secret reference

The `build-hf-space.yml` jobs run with
`environment: ${{ resolve-env.outputs.env_name }}`, so `vars.*` and `secrets.*`
resolve **per environment**.

### `extralit/extralit-hf-space` — Environment **variables** (`vars.*`)

| Variable               | `production` environment      | `staging` environment           |
| ---------------------- | ----------------------------- | ------------------------------- |
| `DOCKER_REPO`          | `extralit/extralit-hf-space`  | `extralitdev/extralit-hf-space` |
| `EXTRALIT_SERVER_IMAGE`| `extralit/extralit-server`    | `extralitdev/extralit-server`   |
| `HF_SPACE_ID`          | `extralit/public-demo`        | `extralit-dev/develop`          |

> These environments were previously named `main` and `develop`. They were
> renamed so the names describe the deploy target rather than a branch, and
> survive any future branch rename.

> The `HF_SPACE_ID` values map to Space URLs `<owner>-<name>.hf.space`:
> `extralit/public-demo` → **extralit-public-demo.hf.space** (the public demo,
> deployed from `release`); `extralit-dev/develop` → extralit-dev-develop.hf.space
> (deployed from `main`). There are **no** repo-level variables in this repo.

> **`EXTRALIT_*` on the `staging` env (consumed by `deploy-pr-space`).** Any
> `EXTRALIT_*` **variable** or **secret** added to the `staging` environment is forwarded
> verbatim onto each `pr-N` Space (§4). Recommended: `EXTRALIT_DATABASE_URL`,
> `EXTRALIT_S3_ACCESS_KEY`/`SECRET_KEY` and `EXTRALIT_AUTH_SECRET_KEY` as **secrets**;
> `EXTRALIT_S3_ENDPOINT`/`REGION`/`SECURE`, `EXTRALIT_BASE_URL`, `EXTRALIT_CORS_ORIGINS`
> as **variables**. Set with `gh secret set <KEY> --env staging` /
> `gh variable set <KEY> --env staging --body <val>`.

### `extralit/extralit-hf-space` — **Secrets** (names only)

| Secret            | Repo-level | `production` env | `staging` env |
| ----------------- | :--------: | :--------------: | :-----------: |
| `HF_TOKEN`        |     —      |        —         |      ✅       |
| `DOCKER_USERNAME` |     —      |        ✅        |      ✅       |
| `DOCKER_PASSWORD` |     —      |        ✅        |      ✅       |

`HF_TOKEN` survives **only** on `staging`, and only for `deploy-pr-space`.
Trusted Publishers scope a token to an *existing* repo, so they cannot cover
`duplicate_space()`, which creates `extralit-dev/pr-N` on demand. That leaves the
remaining token's write access confined to the `extralit-dev` org — nothing can
reach `extralit/public-demo` with a stored credential.

> Deleting the repo-level `HF_TOKEN` is part of this, not an afterthought:
> `secrets.HF_TOKEN` silently falls back to it, so leaving it in place would make
> removing the `production` override purely cosmetic.
>
> **Order matters.** This table is the state *after* a production release has
> deployed keyless end-to-end. Until then both overrides stay, so reverting
> `deploy-space` to a stored token remains a one-commit rollback — deleting them
> early costs nothing on the deploy path (nothing reads `secrets.HF_TOKEN` there
> anymore) but throws away that escape hatch.

### `extralit/extralit` (monorepo)

- **Repo variables:** none.
- **Repo secrets:** `ANTHROPIC_API_KEY`, `GH_ACCESS_TOKEN`.
- **Environments:** `HuggingFace` (no vars/secrets of its own), `copilot`,
  `github-pages`.
- The server/SDK workflows reference secrets like `AR_DOCKER_USERNAME(_DEV)`,
  `AR_DOCKER_PASSWORD(_DEV)`, `GH_ACTIONS_REPOSITORY_DISPATCH`, `CODECOV_TOKEN`,
  `AR_PYPI_API_TOKEN`, and `HF_TOKEN_EXTRALIT_INTERNAL_TESTING`. These are **not**
  defined at the repo or `HuggingFace`-environment level — they are inherited
  from **organization-level** secrets via `secrets: inherit` (reading them
  requires the `admin:org` scope).
- `release.yml` additionally needs a token that can push to `main`, `release`, and
  tags — a GitHub App installation token or a PAT. `GITHUB_TOKEN` is **not**
  sufficient: pushes made with it emit no downstream `push` events, so the tag
  would never trigger the publish, docs, or GitHub-Release workflows. Under branch
  protection this identity also needs a push bypass.

### Workflow-internal GHA env vars (computed at run time)

Beyond the stored `vars.*`/`secrets.*` above, the deploy is driven by env vars
**computed inside the run** from the branch/event. These are what you read in
the Actions logs when debugging a deploy.

**Stage A — `extralit-server.build-docker-images.yml`** (`env:` set per
`is_release`):

| Env var                  | Release (`release` branch)       | Dev (`main` / PR)                 |
| ------------------------ | -------------------------------- | --------------------------------- |
| `IS_RELEASE`             | `true`                           | `false`                           |
| `PLATFORMS`              | `linux/amd64,linux/arm64`        | `linux/amd64`                     |
| `IMAGE_TAG`              | `v<package_version>`             | branch (cleaned) or `pr-N`        |
| `SERVER_DOCKER_IMAGE`    | `extralit/extralit-server`       | `extralitdev/extralit-server`     |
| `HF_SPACES_DOCKER_IMAGE` | `extralit/extralit-hf-space`     | `extralitdev/extralit-hf-space`   |
| `PUBLISH_LATEST`         | `inputs.publish_latest`          | `true` (PR preview: `false`)      |
| `DOCKER_USERNAME/PASSWORD`| `AR_DOCKER_*` secrets            | `AR_DOCKER_*_DEV` secrets         |
| `DISPATCH_BRANCH`        | `github.ref_name`                | `github.ref_name`, or `<n>/merge` when `pr_number` set |

The optional `pr_number` input (set by `extralit-frontend.build-push-dev.yml`)
forces `IMAGE_TAG=pr-N`, `PUBLISH_LATEST=false`, and `DISPATCH_BRANCH=<n>/merge`.
The cross-repo `client-payload` carries the handoff state:
`tag` = `IMAGE_TAG`, `is_release` = `inputs.is_release`, `branch` =
`DISPATCH_BRANCH`.

**Stage B — `build-hf-space.yml`**:

| Env var / output            | Source                                    | Role in deploy                                  |
| --------------------------- | ----------------------------------------- | ----------------------------------------------- |
| `EVENT_NAME`                | `github.event_name`                       | `repository_dispatch` vs `workflow_dispatch`    |
| `PAYLOAD_TAG`               | `client_payload.tag`                      | → `image_tag`                                    |
| `PAYLOAD_BRANCH`            | `client_payload.branch`                   | trunk vs preview routing                         |
| `PAYLOAD_IS_RELEASE`        | `client_payload.is_release`               | **the** production signal; selects `production` env / multi-arch |
| `env_name` *(output)*       | resolved from payload                     | `environment:` → which `vars.*`/`secrets.*` load |
| `image_tag` *(output)*      | payload tag, or `latest` (manual)         | Docker tag built & deployed                      |
| `tag_latest` *(output)*     | `true` on release/trunk                   | also tag/push `:latest`                          |
| `platforms` *(output)*      | `amd64` (staging) / `amd64,arm64` (release) | buildx target platforms                        |
| `pr_space_slug` *(output)*  | `pr-N` / slug for preview refs            | empty → deploy live Space; set → PR preview     |
| `DOCKER_TAGS`               | `${DOCKER_REPO}:${IMAGE_TAG}[,:latest]`   | tags pushed by build job                          |
| `EXTRALIT_SERVER_IMAGE` *(build-arg)* | `vars.EXTRALIT_SERVER_IMAGE`    | base image the Space is built `FROM`             |
| `EXTRALIT_VERSION` *(build-arg)*      | `image_tag`                     | base image tag (→ Dockerfile `ARG`)              |
| `SOURCE_SPACE`              | `extralit-dev/develop` (hardcoded)        | template duplicated for PR preview Spaces        |
| `DOCKER_REPO` (pr job)      | `extralitdev/extralit-hf-space` (hardcoded)| image PR preview Space points at                |

> The `extralit-hf-space` [`Dockerfile`](../../extralit-hf-space/Dockerfile)
> consumes the two build-args as `ARG EXTRALIT_SERVER_IMAGE` and
> `ARG EXTRALIT_VERSION`, resolving `FROM ${EXTRALIT_SERVER_IMAGE}:${EXTRALIT_VERSION}`.

---

## 6. Gotchas & operational notes

- **Nothing reaches production except a release.** Merging to `main` redeploys
  only `extralit-dev/develop`. `extralit/public-demo` moves when — and only when —
  `release.yml` is dispatched with `dry_run=false`.
- **Frontend changes don't auto-deploy the demo Spaces.** A commit touching only
  `extralit-frontend/**` runs `extralit-frontend.yml` (tests + SPA artifact) but
  does **not** trigger `extralit-server.yml` (path filter `extralit-server/**`).
  The live UI goes to Vercel via its native Git integration; the SPA baked into
  the server image only refreshes on the next server build, which picks up the
  latest successful **`main`** frontend artifact — always `main`, release builds
  included (see §3).
- **PR previews cover frontend too.** Marking a **non-fork** PR (server **or**
  frontend) **ready for review** triggers `extralit-frontend.build-push-dev.yml` →
  ephemeral `extralit-dev/pr-N`. It does **not** rebuild on later pushes (by
  design); use **Actions → Deploy PR preview HF Space → Run workflow** with the
  `pr_number` to refresh. That manual path is also the only way to preview a
  **fork** PR (§3a). Previews are dev-org images and never touch `:latest` or
  production.
- **Two Docker orgs.** `extralit/*` = release (from `release`), `extralitdev/*` =
  dev (from `main`/PRs). The Space's `EXTRALIT_SERVER_IMAGE` env var picks which
  base it builds on.
- **A release fires `extralit-server.yml` three times.** The atomic push updates
  `main`, `release` and the `vX.Y.Z` tag at the same SHA. The workflow's
  `concurrency.group` is keyed on `github.ref` (not `github.sha`) precisely so
  those runs don't cancel each other. They do different work: `release` builds and
  ships the production image, the tag publishes to PyPI, and `main` rebuilds the
  dev Space — one extra dev-Space rebuild per release is the accepted cost.
- **Cross-repo token.** The handoff depends on
  `secrets.GH_ACTIONS_REPOSITORY_DISPATCH` (a PAT with dispatch rights on
  `extralit/extralit-hf-space`). If the Space stops updating after merges,
  check this token first.
- **Multi-arch only on release.** Trunk and PR builds are `linux/amd64` only;
  `arm64` is added only for `is_release` builds.
- **Manual recovery.** You can rebuild/redeploy the **staging** Space directly
  from the `extralit-hf-space` repo via **Actions → Build & Deploy HF Space → Run
  workflow**, bypassing the monorepo. To redeploy **production**, re-run the
  original dispatch-triggered run so its `client_payload` (and its `is_release`
  flag) is replayed — a fresh manual dispatch always resolves to staging.

---

## 7. End-to-end summary

### Trunk → dev Space (`main`)

1. PR squash-merged to `main` touching `extralit-server/**`.
2. `extralit-server.yml` → tests, downloads the prebuilt SPA, bundles it, builds wheel.
3. `build_docker_images` (`is_release=false`) → pushes
   `extralitdev/extralit-server:main` (+`:latest`), amd64.
4. `repository_dispatch(build-hf-space, {tag: main, is_release: false, branch: main})`.
5. `build-hf-space.yml` → `resolve-env` (env=`staging`) → builds
   `extralitdev/extralit-hf-space:main` `FROM` the server image.
6. `deploy-space` → commits the digest pin to `extralit-dev/develop`, which rebuilds.
7. Live at **<https://extralit-dev-develop.hf.space>**. **Production untouched.**

### Release → public demo (`release` + tag)

1. `gh workflow run release.yml -f version=X.Y.Z -f dry_run=false`.
2. `release.yml` verifies authorization and green CI on `main`, stamps the version
   via `scripts/bump_version.py set`, and pushes one commit to `main`, `release`,
   and `vX.Y.Z` **atomically**.
3. The `release` push → `extralit-server.yml` → `build_docker_images`
   (`is_release=true`) → `extralit/extralit-server:vX.Y.Z` (+`:latest`), amd64+arm64.
4. `repository_dispatch(build-hf-space, {tag: vX.Y.Z, is_release: true})`.
5. `build-hf-space.yml` → `resolve-env` (env=`production`) → builds
   `extralit/extralit-hf-space:vX.Y.Z` → `deploy-space` commits that image's
   digest to `extralit/public-demo`, which rebuilds.
6. In parallel, the **tag** push drives PyPI (`extralit`, `extralit-server`),
   versioned docs (`mike deploy X.Y` + `stable`), and the GitHub Release.
7. Public demo live at **<https://extralit-public-demo.hf.space>**.

### PR preview → ephemeral Space (`pr-N`)

1. A PR touching `extralit-server/**` or `extralit-frontend/**` is marked **ready
   for review** (or run manually with `pr_number=N`).
2. `extralit-frontend.build-push-dev.yml` → downloads SPA + builds wheel (no pytest).
3. `build_docker_images` (`is_release=false`, `pr_number=N`) → pushes
   `extralitdev/extralit-server:pr-N` (amd64, no `:latest`).
4. `repository_dispatch(build-hf-space, {tag: pr-N, is_release: false, branch: N/merge})`.
5. `build-hf-space.yml` → `resolve-env` (env=`staging`, `pr_space_slug=pr-N`) → builds
   `extralitdev/extralit-hf-space:pr-N`, then `deploy-pr-space` duplicates
   `extralit-dev/develop` → **`extralit-dev/pr-N`** and points it at the image.
6. Preview live at **`https://extralit-dev-pr-N.hf.space`**.
