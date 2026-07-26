import base64
import os

import mkdocs_gen_files
import requests

REPOSITORY = "Extralit/extralit"
CHANGELOG_PATH = "extralit/CHANGELOG.md"
RETRIEVED_BRANCH = "develop"

DATA_PATH = "community/changelog.md"

GITHUB_ACCESS_TOKEN = os.getenv("GH_ACCESS_TOKEN")  # public_repo and read:org scopes are required


def fetch_file_from_github(repository, changelog_path, branch, auth_token):
    if auth_token is None:
        return ""
    headers = {"Authorization": f"Bearer {auth_token}", "Accept": "application/vnd.github.v3+json"}

    owner, repo_name = repository.split("/")
    changelog_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{changelog_path}?ref={branch}"

    print(f"Fetching CHANGELOG.md from {changelog_url}...")
    response = requests.get(changelog_url, headers=headers)

    response_json = response.json()
    if "content" in response_json:
        content = base64.b64decode(response_json["content"]).decode("utf-8")
    else:
        content = ""

    return content


with mkdocs_gen_files.open(DATA_PATH, "w") as f:
    content = fetch_file_from_github(REPOSITORY, CHANGELOG_PATH, RETRIEVED_BRANCH, GITHUB_ACCESS_TOKEN)
    f.write(content)
