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
EMPTY_SCHEMA_NAME = "e2e_v2_empty"
REFERENCE = "10.1000/j.e2e-v2"  # slash on purpose: seam B
WORKSPACE_NAME = "e2e-v2"

BODY = pa.DataFrameSchema(
    columns={
        "size": pa.Column(pa.String, nullable=True),
        "label": pa.Column(pa.String, nullable=True),
        "country": pa.Column(pa.String, nullable=True),
    }
).to_json()

# Coverage-map schema (spec §3.1): one question, zero records — proves the grid still
# renders a column for a schema nobody has annotated yet.
EMPTY_BODY = pa.DataFrameSchema(
    columns={
        "notes": pa.Column(pa.String, nullable=True),
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
            if schema["name"] in (SCHEMA_NAME, EMPTY_SCHEMA_NAME):
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
                        # Neither question is required: the seeded submitted response below
                        # answers only `label` (to prove response-beats-suggestion there while
                        # `size` stays suggestion-sourced) and `PUT .../responses` rejects a
                        # submitted envelope missing any required question's value.
                        "required": False,
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
                            # Deliberately distinct from the `size` suggestion ("120") and the
                            # `label` response ("control") seeded below: if the projection ever
                            # regressed to resolving cells from raw record fields instead of
                            # coalescing suggestion/response, the grid would show these raw
                            # values and the e2e spec's `getByText("999")` count-0 assertion
                            # would catch it. Same field values would otherwise make that
                            # regression invisible to the positive assertions alone.
                            "fields": {
                                "size": "999",
                                "label": "unset",
                                # `country` (not a Question, never projected into the grid) is
                                # the one raw field left carrying a "control" token: the FTS
                                # index (`index/mapping.py::record_to_row`) only ever sees
                                # `record.fields`, never suggestion/response values, so
                                # search-roundtrip.spec.ts's search for "control" needs a raw
                                # field to match now that `label`'s raw value diverges from its
                                # response ("control"). Keeping it here (instead of on
                                # `label`) preserves the size/label raw-vs-coalesced divergence
                                # the grid spec's `getByText("999")` count-0 assertion relies on.
                                "country": "KE-control",
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

        # Competing `label` suggestion + a submitted response that must win the coalesce
        # (spec §3.2 response-beats-suggestion), so the grid proves it, not just the
        # per-reference review form.
        client.put(
            f"/api/v2/records/{record['id']}/suggestions",
            json={
                "question_id": questions["label"]["id"],
                "value": "intervention",
                "score": 0.42,
                "agent": "e2e-seeder",
            },
        ).raise_for_status()
        client.put(
            f"/api/v2/records/{record['id']}/responses",
            json={"values": {"label": {"value": "control"}}, "status": "submitted"},
        ).raise_for_status()

        # Fresh index so the search scenario has something to find.
        client.post(f"/api/v2/schemas/{schema['id']}:rebuild-index").raise_for_status()

        # Coverage-map schema (spec §3.1): one question, zero records.
        empty_schema = (
            client.post(
                "/api/v2/schemas",
                json={"name": EMPTY_SCHEMA_NAME, "workspace_id": workspace["id"]},
            )
            .raise_for_status()
            .json()
        )
        client.post(
            f"/api/v2/schemas/{empty_schema['id']}/versions", json={"body": EMPTY_BODY}
        ).raise_for_status()
        client.post(
            f"/api/v2/schemas/{empty_schema['id']}/questions",
            json={
                "name": "notes",
                "title": "Notes",
                "type": "text",
                "columns": ["notes"],
                "settings": {},
                "required": False,
            },
        ).raise_for_status()

    output = {
        "workspaceId": workspace["id"],
        "schemaId": schema["id"],
        "schemaName": SCHEMA_NAME,
        "emptySchemaName": EMPTY_SCHEMA_NAME,
        "reference": REFERENCE,
        "recordId": record["id"],
        "questions": questions,
    }
    out_path = Path(__file__).parent / "seed-output.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
