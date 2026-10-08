"""Seed deterministic extraction fixtures for the frontend e2e suite.

Usage (from extralit-frontend/):
    uv run --project ../extralit-server python e2e/extraction/seed/seed_v2_e2e.py \
        --api-url http://localhost:6900 --username extralit --password 12345678

Writes e2e/extraction/seed/seed-output.json. Idempotent: deletes and recreates the e2e dataset.
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
                "/api/v1/token",
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

        # Dataset: recreate for determinism.
        existing_datasets = (
            client.get("/api/v1/me/datasets", params={"workspace_id": workspace["id"]})
            .raise_for_status()
            .json()["items"]
        )
        for existing in existing_datasets:
            if existing["name"] in (SCHEMA_NAME, EMPTY_SCHEMA_NAME):
                client.delete(f"/api/v1/datasets/{existing['id']}").raise_for_status()
        dataset = (
            client.post(
                "/api/v1/datasets",
                json={"name": SCHEMA_NAME, "workspace_id": workspace["id"]},
            )
            .raise_for_status()
            .json()
        )

        # The schema version comes first, while the dataset is still a draft: it uploads the
        # Pandera body to object storage and materializes size/label/country as column
        # `Field`s, without touching the dataset's status. Questions can then be created with
        # their `columns` bindings already set, because the columns they bind to now exist
        # (`QuestionColumnBindingValidator` checks against `dataset.fields`) and the dataset is
        # still a draft (`QuestionCreateValidator._validate_dataset_is_not_ready`).
        client.post(
            f"/api/v1/datasets/{dataset['id']}/schema-versions", json={"body": BODY}
        ).raise_for_status()

        # `label_selection` questions don't support column bindings (only text/table
        # questions do), so `label` never gets one.
        questions = {}
        for name, title, required, settings in [
            ("size", "Size", False, {"type": "text", "columns": ["size"]}),
            (
                "label",
                "Label",
                # Exactly one required question, which `DatasetPublishValidator` demands
                # before `PUT /publish` will take the dataset to `ready`. It has to be
                # `label`: the seeded submitted response below answers only `label` (to prove
                # response-beats-suggestion there while `size` stays suggestion-sourced), and
                # `POST .../responses` rejects a submitted envelope missing any required
                # question's value.
                True,
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
                    f"/api/v1/datasets/{dataset['id']}/questions",
                    json={
                        "name": name,
                        "title": title,
                        "settings": settings,
                        "required": required,
                    },
                )
                .raise_for_status()
                .json()
            )
            questions[name] = {"id": question["id"], "name": question["name"]}

        # `PUT /publish` is the sole draft -> ready transition and the sole creator of the
        # search index. A dataset must be ready before records can be bulk-upserted
        # (`RecordsBulkCreateValidator._validate_dataset_is_ready`).
        client.put(f"/api/v1/datasets/{dataset['id']}/publish").raise_for_status()

        records = (
            client.put(
                f"/api/v1/datasets/{dataset['id']}/records/bulk",
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
            f"/api/v1/records/{record['id']}/suggestions",
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
            f"/api/v1/records/{record['id']}/suggestions",
            json={
                "question_id": questions["label"]["id"],
                "value": "intervention",
                "score": 0.42,
                "agent": "e2e-seeder",
            },
        ).raise_for_status()
        client.post(
            f"/api/v1/records/{record['id']}/responses",
            json={"values": {"label": {"value": "control"}}, "status": "submitted"},
        ).raise_for_status()

        # No rebuild-index step: v1 indexes on write, unlike v2's explicit
        # `:rebuild-index` action.

        # Coverage-map schema (spec §3.1): one question, zero records.
        empty_dataset = (
            client.post(
                "/api/v1/datasets",
                json={"name": EMPTY_SCHEMA_NAME, "workspace_id": workspace["id"]},
            )
            .raise_for_status()
            .json()
        )
        # Same order as above: schema version (draft) -> bound question -> publish.
        client.post(
            f"/api/v1/datasets/{empty_dataset['id']}/schema-versions",
            json={"body": EMPTY_BODY},
        ).raise_for_status()
        client.post(
            f"/api/v1/datasets/{empty_dataset['id']}/questions",
            json={
                "name": "notes",
                "title": "Notes",
                "settings": {"type": "text", "columns": ["notes"]},
                # `DatasetPublishValidator` needs at least one required question; this
                # dataset has no records, so nothing has to answer it.
                "required": True,
            },
        ).raise_for_status()
        client.put(f"/api/v1/datasets/{empty_dataset['id']}/publish").raise_for_status()

    output = {
        "workspaceId": workspace["id"],
        "schemaId": dataset["id"],
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
