# Deployment & CI/CD Architecture

How a code change in any monorepo module flows through GitHub Actions to the
public demo at **<https://extralit-public-demo.hf.space>**.

This document traces the end-to-end pipeline that turns a commit into a running
Hugging Face Space. The terminal step is
[`extralit-hf-space/.github/workflows/build-hf-space.yml`](../../extralit-hf-space/.github/workflows/build-hf-space.yml),
which lives in the **separate** `extralit/extralit-hf-space` repository (vendored
here as a git submodule).

---

## 1. The big picture

The pipeline spans **two repositories** and is glued together by a GitHub
`repository_dispatch` event:

```mermaid
flowchart TD
    subgraph monorepo["Repo: extralit/extralit (monorepo)"]
        push["git push / merge"]
        prready["PR ready_for_review / manual dispatch"]
        fe[".github/workflows/extralit-frontend.yml"]
        sdk[".github/workflows/extralit.yml"]
        srv[".github/workflows/extralit-server.yml"]
        prev[".github/workflows/extralit-pr-preview.yml"]
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
        prspace["PR preview Space: extralit-dev/pr-N"]
    end

    push --> fe
    push --> sdk
    push --> srv
    prready -->|server OR frontend PR| prev
    srv -->|tests + builds frontend dist + wheel| srvbuild
    prev -->|builds frontend dist + wheel| srvbuild
    srvbuild -->|build & push| srvimg
    srvbuild -->|repository_dispatch: build-hf-space| bhs
    bhs -->|FROM server image + ES/Redis/OCR| spaceimg
    bhs -->|restart| demo
    bhs -->|duplicate + retarget| prspace
```

**Key insight:** the HF Space image is built **`FROM` the `extralit-server`
image**. The server image, in turn, bundles the **compiled frontend** at build
time. So the demo is rebuilt by whichever workflow rebuilds that server image:
the **`extralit-server`** workflow drives `main`/`develop`, and a dedicated
**`extralit-pr-preview`** workflow drives per-PR ephemeral Spaces (it rebuilds the
same server image — frontend baked in — so frontend-only PRs get a preview too).
Both hand off to the same `build-docker-images.yml` + `repository_dispatch`. See
[§6 Gotchas](#6-gotchas--operational-notes).

---

## 2. Module → workflow routing

Each module has its own workflow, gated by `paths:` filters so unrelated changes
don't trigger unrelated builds.

| Module (dir)        | Workflow                          | Triggers on path                              | Produces                                            | Reaches the demo? |
| ------------------- | --------------------------------- | --------------------------------------------- | --------------------------------------------------- | ----------------- |
| `extralit-server/`  | `extralit-server.yml`             | `extralit-server/**` (push/PR)                | `extralit-server` Docker image + PyPI wheel         | **Yes** (`main`/`develop`) |
| `extralit-frontend/`| `extralit-frontend.yml`           | `extralit-frontend/**`                        | Frontend `dist/` artifact (tests/lint only)         | Indirect¹         |
| *(server **or** frontend PR)* | `extralit-pr-preview.yml` | PR `ready_for_review` on `extralit-server/**` **or** `extralit-frontend/**`; or manual `pr_number` | `extralitdev/extralit-server:pr-N` image → ephemeral Space | **Yes** (`extralit-dev/pr-N`) |
| `extralit/` (SDK)   | `extralit.yml`                    | `extralit/**` (excl. `docs/`, `mkdocs.yml`)   | `extralit` PyPI wheel                               | No²               |
| `extralit-hf-space/`| `build-hf-space.yml` *(other repo)* | repository_dispatch / manual                | `extralit-hf-space` Docker image + Space restart/deploy | **Yes** (terminal) |

¹ The frontend's own workflow only tests and uploads a `dist` artifact. The
frontend that actually ships is **recompiled from source inside the server
build** (see §3). A frontend-only change does not redeploy the **public** demo on
its own — that still needs the server/`main` flow — but a frontend-only **PR**
*does* get an ephemeral preview: `extralit-pr-preview.yml` rebuilds the server
image (frontend baked in) and deploys `extralit-dev/pr-N` (see §3a).

² The SDK is published to PyPI and is *consumed by* the demo's CI for
integration tests (it spins up `extralitdev/extralit-hf-space:latest` as a
service container), but SDK changes never rebuild the Space image.

---

## 3. Stage A — `extralit-server.yml` (in the monorepo)

File: [`.github/workflows/extralit-server.yml`](../../.github/workflows/extralit-server.yml)

Triggered by push to `main`/`develop`/`releases/**`, by non-fork PRs, or
manually (`workflow_dispatch`).

### Job `build`
1. Spins up service containers (Elasticsearch, Postgres, Redis, MinIO) and runs
   `pytest tests/unit` with coverage → Codecov.
2. **Compiles the frontend from source** (`npm install && npm run build` in
   `extralit-frontend/`) using `BASE_URL=@@baseUrl@@` (a placeholder rewritten at
   runtime to support a parameterizable root path).
3. Copies `extralit-frontend/dist` into `src/extralit_server/static`, then
   `uv build` → uploads the `extralit-server` wheel artifact.

### Job `build_docker_images` → `extralit-server.build-docker-images.yml`
File: [`.github/workflows/extralit-server.build-docker-images.yml`](../../.github/workflows/extralit-server.build-docker-images.yml)

Runs only on `main` / `develop` / `releases/**` / `workflow_dispatch` / non-fork
non-draft PRs.

| Input                  | `is_release` (main / dispatch) | dev (develop / PR)              |
| ---------------------- | ------------------------------ | ------------------------------- |
| Docker org             | `extralit/extralit-server`     | `extralitdev/extralit-server`   |
| Platforms              | `linux/amd64,linux/arm64`      | `linux/amd64`                   |
| Image tag              | `v<package_version>`           | branch name (cleaned) or `pr-N` |
| Publish `:latest`      | only on `main`                 | dev `:latest`, except PR previews (`pr_number` set) |

The tag is derived by the
[`docker-image-tag-from-ref`](../../.github/actions/docker-image-tag-from-ref)
composite action: tags → `<tag>`, PRs → `pr-<number>`, branches →
`<branch>` with non-alphanumerics replaced by `-`.

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

> The `publish_release` job additionally publishes the `extralit-server` wheel to
> (Test)PyPI on `main`/dispatch. Not part of the Space deploy.

---

## 3a. PR preview — `extralit-pr-preview.yml` (in the monorepo)

File: [`.github/workflows/extralit-pr-preview.yml`](../../.github/workflows/extralit-pr-preview.yml)

A single-purpose workflow that gives any server- **or** frontend-touching PR an
ephemeral Space, deliberately decoupled from `extralit-server.yml` so it does
**not** run on every push:

- **Auto:** `pull_request: types: [ready_for_review]` on `extralit-server/**` or
  `extralit-frontend/**`. Marking a PR ready (not each subsequent push) builds the
  preview; refresh later via the manual path. (`ready_for_review` only fires on a
  draft→ready transition — a PR opened directly as non-draft won't auto-trigger;
  re-mark it ready or use the manual path.)
- **Manual:** `workflow_dispatch` with a `pr_number` input — (re)deploy a chosen PR
  on demand.

Its `build` job mirrors the frontend+wheel steps from §3 (no pytest), then calls
the same [`build-docker-images.yml`](../../.github/workflows/extralit-server.build-docker-images.yml)
with `is_release: false` and `pr_number`. Result: `extralitdev/extralit-server:pr-N`
is pushed and the dispatch (`branch=<n>/merge`) drives the HF Space repo's
`deploy-pr-space` job → **`extralit-dev/pr-N`** (`extralit-dev-pr-N.hf.space`).
`main`/`develop` deploys are untouched and still flow through §3.

---

## 4. Stage B — `build-hf-space.yml` (in `extralit/extralit-hf-space`)

File: [`extralit-hf-space/.github/workflows/build-hf-space.yml`](../../extralit-hf-space/.github/workflows/build-hf-space.yml)

Entry points:
- **`repository_dispatch` / `build-hf-space`** — the automated path from Stage A.
- **`workflow_dispatch`** — manual rebuild of the current ref (`develop` env, tag
  `latest`, amd64 only).

### Job `resolve-env`
Pure-bash step that maps the dispatch payload to build parameters:

| Source branch / event                | `env_name` | `image_tag`        | `tag_latest` | `platforms`                 | `pr_space_slug` |
| ------------------------------------- | ---------- | ------------------ | ------------ | --------------------------- | --------------- |
| `is_release=true` → `main`            | `main`     | payload `tag` (`v…`) | `true`     | `amd64,arm64`               | — (empty)       |
| `branch=develop`                      | `develop`  | payload `tag`      | `true`       | `amd64`                     | — (empty)       |
| any other branch (PR)                 | `develop`  | payload `tag`      | `false`      | `amd64`                     | `pr-N` / slug   |
| `workflow_dispatch`                   | per ref    | `latest`           | `false`/`true`| `amd64`                     | per ref         |

`env_name` selects the GitHub **Environment** (`main` vs `develop`), which is how
per-environment secrets/vars are scoped: `DOCKER_REPO`, `EXTRALIT_SERVER_IMAGE`,
`HF_SPACE_ID`, `HF_TOKEN`, `DOCKER_USERNAME`/`DOCKER_PASSWORD`.

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
`extralit/extralit-hf-space` (main) or `extralitdev/extralit-hf-space` (dev),
tagging `:latest` when `tag_latest=true`.

### Job `deploy-space` — *non-PR builds only* (`pr_space_slug == ''`)
Restarts the live Space so it pulls the freshly pushed image:

```bash
curl -X POST "https://huggingface.co/api/spaces/${HF_SPACE_ID}/restart" \
     -H "Authorization: Bearer $HF_TOKEN"
```

`HF_SPACE_ID` is the environment-scoped Space (see §5): the **`main`**
environment points at `extralit/public-demo` — the live public demo served at
**<https://extralit-public-demo.hf.space>** — while the **`develop`**
environment points at `extralit-dev/develop`
(`extralit-dev-develop.hf.space`).

### Job `deploy-pr-space` — *PR builds only* (`pr_space_slug != ''`)
Runs under `environment: develop`. Creates an ephemeral preview Space per PR:
1. `duplicate_space("extralit-dev/develop" → "extralit-dev/pr-N")` (cpu-basic) on
   first run, writing a README that enables `app_port: 6900`.
2. **Propagates config.** `duplicate_space` copies files but **not** secrets/variables,
   so the job forwards the `develop` GitHub environment's `EXTRALIT_*` onto the Space —
   env **secrets** → `add_space_secret`, env **variables** → `add_space_variable`. It
   strictly filters to the `EXTRALIT_` prefix (via `toJSON(secrets)`/`toJSON(vars)`), so
   `HF_TOKEN`/`DOCKER_*`/the GitHub token are never pushed; only keys are logged.
3. Uploads a one-line `Dockerfile` (`FROM extralitdev/extralit-hf-space:pr-N`) so
   the preview Space tracks the PR's image.

> **OAuth is not wired for previews.** The custom HF OAuth app is pinned to the
> `extralit-dev-develop.hf.space` callback and can't serve ephemeral `pr-N` domains, so
> sign-in won't work on a preview. Do **not** put `EXTRALIT_ELASTICSEARCH`/
> `EXTRALIT_REDIS_URL` in the `develop` env — the bundle runs its own ES/Redis at
> `localhost` and the generic filter would otherwise override them.

---

## 5. Environment & secret reference

Resolved live from GitHub on 2026-06-10 via `gh api`. The `build-hf-space.yml`
jobs run with `environment: ${{ resolve-env.outputs.env_name }}`, so `vars.*` and
`secrets.*` resolve **per environment**.

### `extralit/extralit-hf-space` — Environment **variables** (`vars.*`)

| Variable               | `main` environment            | `develop` environment           |
| ---------------------- | ----------------------------- | ------------------------------- |
| `DOCKER_REPO`          | `extralit/extralit-hf-space`  | `extralitdev/extralit-hf-space` |
| `EXTRALIT_SERVER_IMAGE`| `extralit/extralit-server`    | `extralitdev/extralit-server`   |
| `HF_SPACE_ID`          | `extralit/public-demo`        | `extralit-dev/develop`          |

> The `HF_SPACE_ID` values map to Space URLs `<owner>-<name>.hf.space`:
> `extralit/public-demo` → **extralit-public-demo.hf.space** (the public demo,
> deployed from `main`); `extralit-dev/develop` → extralit-dev-develop.hf.space.
> There are **no** repo-level variables in this repo.

> **`EXTRALIT_*` on the `develop` env (consumed by `deploy-pr-space`).** Any
> `EXTRALIT_*` **variable** or **secret** added to the `develop` environment is forwarded
> verbatim onto each `pr-N` Space (§4). Recommended: `EXTRALIT_DATABASE_URL`,
> `EXTRALIT_S3_ACCESS_KEY`/`SECRET_KEY` and `EXTRALIT_AUTH_SECRET_KEY` as **secrets**;
> `EXTRALIT_S3_ENDPOINT`/`REGION`/`SECURE`, `EXTRALIT_BASE_URL`, `EXTRALIT_CORS_ORIGINS`
> as **variables**. Set with `gh secret set <KEY> --env develop` /
> `gh variable set <KEY> --env develop --body <val>`.

### `extralit/extralit-hf-space` — **Secrets** (names only)

| Secret            | Repo-level | `main` env | `develop` env |
| ----------------- | :--------: | :--------: | :-----------: |
| `HF_TOKEN`        | ✅ (default) | ✅ (override) | ✅ (override) |
| `DOCKER_USERNAME` |     —      |     ✅      |      ✅       |
| `DOCKER_PASSWORD` |     —      |     ✅      |      ✅       |

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

### Workflow-internal GHA env vars (computed at run time)

Beyond the stored `vars.*`/`secrets.*` above, the deploy is driven by env vars
**computed inside the run** from the branch/event. These are what you read in
the Actions logs when debugging a deploy.

**Stage A — `extralit-server.build-docker-images.yml`** (`env:` set per
`is_release`):

| Env var                  | Release (`main` / dispatch)      | Dev (`develop` / PR)              |
| ------------------------ | -------------------------------- | --------------------------------- |
| `IS_RELEASE`             | `true`                           | `false`                           |
| `PLATFORMS`              | `linux/amd64,linux/arm64`        | `linux/amd64`                     |
| `IMAGE_TAG`              | `v<package_version>`             | branch (cleaned) or `pr-N`        |
| `SERVER_DOCKER_IMAGE`    | `extralit/extralit-server`       | `extralitdev/extralit-server`     |
| `HF_SPACES_DOCKER_IMAGE` | `extralit/extralit-hf-space`     | `extralitdev/extralit-hf-space`   |
| `PUBLISH_LATEST`         | `inputs.publish_latest` (main)   | `true` (PR preview: `false`)      |
| `DOCKER_USERNAME/PASSWORD`| `AR_DOCKER_*` secrets            | `AR_DOCKER_*_DEV` secrets         |
| `DISPATCH_BRANCH`        | `github.ref_name`                | `github.ref_name`, or `<n>/merge` when `pr_number` set |

The optional `pr_number` input (set by `extralit-pr-preview.yml`'s manual path)
forces `IMAGE_TAG=pr-N`, `PUBLISH_LATEST=false`, and `DISPATCH_BRANCH=<n>/merge`.
The cross-repo `client-payload` carries the handoff state:
`tag` = `IMAGE_TAG`, `is_release` = `inputs.is_release`, `branch` =
`DISPATCH_BRANCH`.

**Stage B — `build-hf-space.yml`**:

| Env var / output            | Source                                    | Role in deploy                                  |
| --------------------------- | ----------------------------------------- | ----------------------------------------------- |
| `EVENT_NAME`                | `github.event_name`                       | `repository_dispatch` vs `workflow_dispatch`    |
| `PAYLOAD_TAG`               | `client_payload.tag`                      | → `image_tag`                                    |
| `PAYLOAD_BRANCH`            | `client_payload.branch`                   | branch routing                                   |
| `PAYLOAD_IS_RELEASE`        | `client_payload.is_release`               | selects `main` env / multi-arch                  |
| `env_name` *(output)*       | resolved from branch/payload              | `environment:` → which `vars.*`/`secrets.*` load |
| `image_tag` *(output)*      | payload tag, or `latest` (manual)         | Docker tag built & deployed                      |
| `tag_latest` *(output)*     | `true` on main/develop                    | also tag/push `:latest`                          |
| `platforms` *(output)*      | `amd64` (dev) / `amd64,arm64` (release)   | buildx target platforms                          |
| `pr_space_slug` *(output)*  | `pr-N` / slug for non-main/develop        | empty → restart live Space; set → PR preview     |
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

- **Frontend changes don't auto-deploy the *public* demo.** A commit touching only
  `extralit-frontend/**` runs `extralit-frontend.yml` (tests + artifact) but does
  **not** trigger `extralit-server.yml` (path filter `extralit-server/**`), so it
  doesn't redeploy `extralit/public-demo`. The shipped frontend is rebuilt from
  source *inside* the server build. To roll a frontend-only change to the public
  demo, merge to `main`/`develop` via the server flow.
- **PR previews cover frontend too.** Marking a PR (server **or** frontend)
  **ready for review** triggers `extralit-pr-preview.yml` → ephemeral
  `extralit-dev/pr-N`. It does **not** rebuild on later pushes (by design); use
  **Actions → Deploy PR preview HF Space → Run workflow** with the `pr_number` to
  refresh. Previews are dev-org images and never touch `:latest` or production.
- **Two Docker orgs.** `extralit/*` = release (from `main`), `extralitdev/*` =
  dev (from `develop`/PRs). The demo's `EXTRALIT_SERVER_IMAGE` env var picks
  which base it builds on.
- **Cross-repo token.** The handoff depends on
  `secrets.GH_ACTIONS_REPOSITORY_DISPATCH` (a PAT with dispatch rights on
  `extralit/extralit-hf-space`). If the Space stops updating after server merges,
  check this token first.
- **Multi-arch only on release.** Dev/develop builds are `linux/amd64` only;
  `arm64` is added only for `is_release` (main) builds.
- **Manual recovery.** You can rebuild/redeploy the Space directly from the
  `extralit-hf-space` repo via **Actions → Build & Deploy HF Space → Run
  workflow** (`workflow_dispatch`), bypassing the monorepo entirely.

---

## 7. End-to-end summary

### Release → public demo (`main`)

1. PR merged to `main` touching `extralit-server/**`.
2. `extralit-server.yml` → tests, builds frontend `dist`, bundles it, builds wheel.
3. `build_docker_images` (`is_release=true`) → pushes
   `extralit/extralit-server:v<version>` (+`:latest`), multi-arch amd64+arm64.
4. `repository_dispatch(build-hf-space, {tag: v<version>, is_release: true})` → fires.
5. `build-hf-space.yml` → `resolve-env` (env=`main`) → builds
   `extralit/extralit-hf-space:v<version>` `FROM` the server image.
6. `deploy-space` → `POST /spaces/extralit/public-demo/restart`.
7. Public demo live at **<https://extralit-public-demo.hf.space>**.

### Staging (`develop`)

Same flow, env=`develop`: `extralitdev/*` images tagged `develop` (+`:latest`,
amd64-only), restarting `extralit-dev/develop` → extralit-dev-develop.hf.space.

### PR preview → ephemeral Space (`pr-N`)

1. A PR touching `extralit-server/**` or `extralit-frontend/**` is marked **ready
   for review** (or run manually with `pr_number=N`).
2. `extralit-pr-preview.yml` → builds frontend `dist` + wheel (no pytest).
3. `build_docker_images` (`is_release=false`, `pr_number=N`) → pushes
   `extralitdev/extralit-server:pr-N` (amd64, no `:latest`).
4. `repository_dispatch(build-hf-space, {tag: pr-N, is_release: false, branch: N/merge})`.
5. `build-hf-space.yml` → `resolve-env` (env=`develop`, `pr_space_slug=pr-N`) → builds
   `extralitdev/extralit-hf-space:pr-N`, then `deploy-pr-space` duplicates
   `extralit-dev/develop` → **`extralit-dev/pr-N`** and points it at the image.
6. Preview live at **`https://extralit-dev-pr-N.hf.space`**.
