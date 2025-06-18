---
description: Step-by-step guide for creating a new Extralit release
hide:
 - footer
---

# Extralit Release Guide

This guide provides a simplified, step-by-step process for creating a new release of Extralit. Follow these steps to ensure a smooth and consistent release process.

**Tips:**
- Always update the version in `src/argilla/_version.py` before tagging.
- Use clear, descriptive release notes.
- Coordinate with other maintainers if needed.

## 1. Prepare the Release Branch

- Ensure all features and fixes for the release are merged into `develop`.
- Create a release branch from `develop`:
  ```sh
  git checkout develop
  git pull origin develop
  git checkout -b releases/vX.Y.Z
  git push origin releases/vX.Y.Z
  ```

## 2. Open Pull Requests

- Open a PR from `releases/vX.Y.Z` into `develop` (if any last-minute fixes are needed).
- Open a PR from `releases/vX.Y.Z` into `main`.
- Use "Squash and merge" for a clean history if desired.

## 3. Merge and Tag the Release

- After merging into `main`, checkout `main` locally and pull the latest changes:
  ```sh
  git checkout main
  git pull origin main
  ```
- Tag the release:
  ```sh
  git tag vX.Y.Z
  git push origin vX.Y.Z
  ```

## 4. Create the GitHub Release

- Go to the [GitHub Releases page](https://github.com/extralit/extralit/releases).
- Click "Draft a new release".
- Set the tag to `vX.Y.Z`.
- Add release notes (see previous releases for examples).
- Publish the release.

## 5. Verify the Release

- Monitor GitHub Actions to ensure the release workflow completes successfully.
- Check [PyPI](https://pypi.org/project/extralit/) to confirm the new version is published.
- Test the CLI:
  ```sh
  pip install --upgrade extralit
  extralit --help
  ```

## 6. Announce the Release

- Share the release notes with the community (Slack, GitHub Discussions, etc.).

