"""Seed deterministic v2 fixtures for the frontend e2e suite.

Usage (from extralit-frontend/):
    uv run --project ../extralit-server python e2e/v2/seed/seed_v2_e2e.py \
        --api-url http://localhost:6900 --username extralit --password 12345678

Writes e2e/v2/seed/seed-output.json. Idempotent: deletes and recreates the e2e schema.
"""

import argparse
import json
from pathlib import Path

import httpx
import pandera.pandas as pa

SCHEMA_NAME = "e2e_v2_slice"
REFERENCE = "10.1000/j.e2e-v2"  # slash on purpose: seam B
WORKSPACE_NAME = "e2e-v2"

BODY = pa.DataFrameSchema(
    columns={
        "size": pa.Column(pa.String, nullable=True),
        "label": pa.Column(pa.String, nullable=True),
        "country": pa.Column(pa.String, nullable=True),
    }
).to_json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:6900")
    parser.add_argument("--username", default="extralit")
    parser.add_argument("--password", default="12345678")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        token = (
            client.post(
                "/api/v2/token",
                data={"username": args.username, "password": args.password},
            )
            .raise_for_status()
            .json()["access_token"]
        )
        client.headers["Authorization"] = f"Bearer {token}"

        # Workspace (v1 API): reuse if it exists.
        workspaces = (
            client.get("/api/v1/me/workspaces").raise_for_status().json()["items"]
        )
        workspace = next((w for w in workspaces if w["name"] == WORKSPACE_NAME), None)
        if workspace is None:
            workspace = (
                client.post("/api/v1/workspaces", json={"name": WORKSPACE_NAME})
                .raise_for_status()
                .json()
            )

        # Schema: recreate for determinism.
        schemas = (
            client.get("/api/v2/schemas", params={"workspace_id": workspace["id"]})
            .raise_for_status()
            .json()["items"]
        )
        for schema in schemas:
            if schema["name"] == SCHEMA_NAME:
                client.delete(f"/api/v2/schemas/{schema['id']}").raise_for_status()
        schema = (
            client.post(
                "/api/v2/schemas",
                json={"name": SCHEMA_NAME, "workspace_id": workspace["id"]},
            )
            .raise_for_status()
            .json()
        )

        client.post(
            f"/api/v2/schemas/{schema['id']}/versions", json={"body": BODY}
        ).raise_for_status()

        questions = {}
        for name, qtype, settings in [
            ("size", "text", {}),
            (
                "label",
                "label_selection",
                {
                    "type": "label_selection",
                    "options": [
                        {
                            "value": "intervention",
                            "text": "Intervention",
                            "description": None,
                        },
                        {"value": "control", "text": "Control", "description": None},
                    ],
                },
            ),
        ]:
            question = (
                client.post(
                    f"/api/v2/schemas/{schema['id']}/questions",
                    json={
                        "name": name,
                        "title": name.title(),
                        "type": qtype,
                        "columns": [name],
                        "settings": settings,
                        "required": name == "size",
                    },
                )
                .raise_for_status()
                .json()
            )
            questions[name] = {"id": question["id"], "name": question["name"]}

        records = (
            client.post(
                f"/api/v2/schemas/{schema['id']}/records:bulk-upsert",
                json={
                    "items": [
                        {
                            "fields": {
                                "size": "120",
                                "label": "control",
                                "country": "KE",
                            },
                            "reference": REFERENCE,
                        }
                    ]
                },
            )
            .raise_for_status()
            .json()["items"]
        )
        record = records[0]

        client.put(
            f"/api/v2/records/{record['id']}/suggestions",
            json={
                "question_id": questions["size"]["id"],
                "value": "120",
                "score": 0.87,
                "agent": "e2e-seeder",
            },
        ).raise_for_status()

        # Fresh index so the search scenario has something to find.
        client.post(f"/api/v2/schemas/{schema['id']}:rebuild-index").raise_for_status()

    output = {
        "workspaceId": workspace["id"],
        "schemaId": schema["id"],
        "schemaName": SCHEMA_NAME,
        "reference": REFERENCE,
        "recordId": record["id"],
        "questions": questions,
    }
    out_path = Path(__file__).parent / "seed-output.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
