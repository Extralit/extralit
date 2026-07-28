"""Seed a richer, demo-grade v2 workspace for the /extractions grid demo video.

Unlike e2e/extraction/seed/seed_v2_e2e.py (a minimal, assertion-shaped fixture), this builds a
realistic malaria-systematic-review workspace that exercises every grid affordance:

  * `study_characteristics` — 3 scalar questions, agent suggestions with scores
  * `outcomes`              — a TABLE question (arms/n/incidence) that fans a reference out
                              to several stacked rows (drives reference-group banding)
  * `risk_of_bias`          — a schema with ZERO records: a coverage-gap column manifest
  * one human submitted response that must beat its competing agent suggestion
  * deliberate holes (missing suggestions) so null cells / coverage gaps are visible

Idempotent: each schema is dropped and recreated, so re-running produces the same grid.

Usage:  uv run --project ../../extralit-server python seed_demo_workspace.py --output <path>
"""

import argparse
import json
from pathlib import Path

import httpx
import pandera.pandas as pa

WORKSPACE_NAME = "malaria-demo"
EMPTY_WORKSPACE_NAME = "empty-demo"
CHARS_SCHEMA = "study_characteristics"
OUTCOMES_SCHEMA = "outcomes"
ROB_SCHEMA = "risk_of_bias"

# (reference, country, design, sample_size, arms[], human_label_override)
STUDIES = [
    (
        "10.1016/S0140-6736(21)01812-1",
        "Kenya",
        "cluster-RCT",
        "4812",
        [
            {"arm": "ITN + IRS", "n": "2401", "incidence": "0.21"},
            {"arm": "ITN only", "n": "2411", "incidence": "0.34"},
        ],
        None,
    ),
    (
        "10.1056/NEJMoa2026330",
        "Tanzania",
        "individually-randomised",
        "1720",
        [
            {"arm": "RTS,S/AS01", "n": "860", "incidence": "0.11"},
            {"arm": "Placebo", "n": "860", "incidence": "0.29"},
        ],
        None,
    ),
    (
        "10.1186/s12936-022-04101-0",
        "Uganda",
        "cluster-RCT",
        "9330",
        [
            {"arm": "PBO net", "n": "3110", "incidence": "0.18"},
            {"arm": "Standard net", "n": "3110", "incidence": "0.27"},
            {"arm": "No net", "n": "3110", "incidence": "0.41"},
        ],
        None,
    ),
    (
        "10.1371/journal.pmed.1003844",
        "Burkina Faso",
        # Agent suggested "cohort"; a human reviewer submitted "cluster-RCT" — the grid must
        # show the human answer, not the agent's.
        "cohort",
        "2064",
        [{"arm": "SMC + vaccine", "n": "1032", "incidence": "0.09"}],
        "cluster-RCT",
    ),
    (
        "10.1093/cid/ciab1049",
        "Nigeria",
        "case-control",
        None,  # deliberate hole: no sample_size suggestion -> null cell
        [
            {"arm": "Cases", "n": "412", "incidence": "0.55"},
            {"arm": "Controls", "n": "824", "incidence": "0.12"},
        ],
        None,
    ),
    (
        "10.1016/j.ijid.2023.02.014",
        "Mozambique",
        "cross-sectional",
        "1188",
        [],  # deliberate hole: no outcomes record at all -> outcome columns blank
        None,
    ),
    (
        "10.4269/ajtmh.22-0417",
        None,  # deliberate hole: no country suggestion
        "cluster-RCT",
        "7402",
        [
            {"arm": "IRS rotation", "n": "3701", "incidence": "0.16"},
            {"arm": "Control", "n": "3701", "incidence": "0.30"},
        ],
        None,
    ),
    (
        "10.1101/2024.03.11.24304102",
        "Ghana",
        "quasi-experimental",
        "560",
        [{"arm": "Reactive case detection", "n": "560", "incidence": "0.24"}],
        None,
    ),
]

CHARS_BODY = pa.DataFrameSchema(
    columns={
        "country": pa.Column(pa.String, nullable=True),
        "design": pa.Column(pa.String, nullable=True),
        "sample_size": pa.Column(pa.String, nullable=True),
    }
).to_json()

OUTCOMES_BODY = pa.DataFrameSchema(
    columns={
        "arm": pa.Column(pa.String, nullable=True),
        "n": pa.Column(pa.String, nullable=True),
        "incidence": pa.Column(pa.String, nullable=True),
    }
).to_json()

ROB_BODY = pa.DataFrameSchema(
    columns={
        "randomization": pa.Column(pa.String, nullable=True),
        "blinding": pa.Column(pa.String, nullable=True),
    }
).to_json()

AGENT = "gpt-extractor-v2"


def recreate_schema(
    client: httpx.Client, workspace_id: str, name: str, body: str
) -> dict:
    existing = (
        client.get("/api/v2/schemas", params={"workspace_id": workspace_id})
        .raise_for_status()
        .json()["items"]
    )
    for schema in existing:
        if schema["name"] == name:
            client.delete(f"/api/v2/schemas/{schema['id']}").raise_for_status()
    schema = (
        client.post(
            "/api/v2/schemas", json={"name": name, "workspace_id": workspace_id}
        )
        .raise_for_status()
        .json()
    )
    client.post(
        f"/api/v2/schemas/{schema['id']}/versions", json={"body": body}
    ).raise_for_status()
    return schema


def add_question(
    client: httpx.Client, schema_id: str, *, name, title, qtype, columns, settings=None
) -> dict:
    return (
        client.post(
            f"/api/v2/schemas/{schema_id}/questions",
            json={
                "name": name,
                "title": title,
                "type": qtype,
                "columns": columns,
                "settings": settings or {},
                "required": False,
            },
        )
        .raise_for_status()
        .json()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:6900")
    parser.add_argument("--username", default="extralit")
    parser.add_argument("--password", default="12345678")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("demo-seed.json"),
        help="where to write the seed manifest the Playwright driver reads",
    )
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_url, timeout=60) as client:
        token = (
            client.post(
                "/api/v2/token",
                data={"username": args.username, "password": args.password},
            )
            .raise_for_status()
            .json()["access_token"]
        )
        client.headers["Authorization"] = f"Bearer {token}"

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
        workspace_id = workspace["id"]

        chars = recreate_schema(client, workspace_id, CHARS_SCHEMA, CHARS_BODY)
        outcomes = recreate_schema(client, workspace_id, OUTCOMES_SCHEMA, OUTCOMES_BODY)
        rob = recreate_schema(client, workspace_id, ROB_SCHEMA, ROB_BODY)

        q_country = add_question(
            client,
            chars["id"],
            name="country",
            title="Country",
            qtype="text",
            columns=["country"],
        )
        q_design = add_question(
            client,
            chars["id"],
            name="design",
            title="Study design",
            qtype="label_selection",
            columns=["design"],
            settings={
                "type": "label_selection",
                "options": [
                    {"value": v, "text": v, "description": None}
                    for v in [
                        "cluster-RCT",
                        "individually-randomised",
                        "cohort",
                        "case-control",
                        "cross-sectional",
                        "quasi-experimental",
                    ]
                ],
            },
        )
        q_size = add_question(
            client,
            chars["id"],
            name="sample_size",
            title="Sample size",
            qtype="text",
            columns=["sample_size"],
        )

        # TABLE question: each element of the value array becomes its own grid row for that
        # reference (spec §3.4 fan-out) — this is what makes the banding visible.
        q_arms = add_question(
            client,
            outcomes["id"],
            name="arms",
            title="Trial arms",
            qtype="table",
            columns=["arm", "n", "incidence"],
        )

        # risk_of_bias: questions but ZERO records -> coverage-gap columns.
        add_question(
            client,
            rob["id"],
            name="randomization",
            title="Randomization",
            qtype="text",
            columns=["randomization"],
        )
        add_question(
            client,
            rob["id"],
            name="blinding",
            title="Blinding",
            qtype="text",
            columns=["blinding"],
        )

        char_items = [
            {"fields": {"source": "pdf"}, "reference": ref} for ref, *_ in STUDIES
        ]
        char_records = (
            client.post(
                f"/api/v2/schemas/{chars['id']}/records:bulk-upsert",
                json={"items": char_items},
            )
            .raise_for_status()
            .json()["items"]
        )
        char_by_ref = {r["reference"]: r["id"] for r in char_records}

        outcome_refs = [ref for ref, _, _, _, arms, _ in STUDIES if arms]
        outcome_records = (
            client.post(
                f"/api/v2/schemas/{outcomes['id']}/records:bulk-upsert",
                json={
                    "items": [
                        {"fields": {"source": "pdf"}, "reference": ref}
                        for ref in outcome_refs
                    ]
                },
            )
            .raise_for_status()
            .json()["items"]
        )
        outcome_by_ref = {r["reference"]: r["id"] for r in outcome_records}

        for reference, country, design, sample_size, arms, human_design in STUDIES:
            record_id = char_by_ref[reference]
            for question, value, score in [
                (q_country, country, 0.93),
                (q_design, design, 0.71),
                (q_size, sample_size, 0.88),
            ]:
                if value is None:
                    continue  # deliberate hole -> null cell
                client.put(
                    f"/api/v2/records/{record_id}/suggestions",
                    json={
                        "question_id": question["id"],
                        "value": value,
                        "score": score,
                        "agent": AGENT,
                    },
                ).raise_for_status()

            if human_design is not None:
                # Submitted human response must beat the competing agent suggestion.
                client.put(
                    f"/api/v2/records/{record_id}/responses",
                    json={
                        "values": {"design": {"value": human_design}},
                        "status": "submitted",
                    },
                ).raise_for_status()

            if arms:
                client.put(
                    f"/api/v2/records/{outcome_by_ref[reference]}/suggestions",
                    json={
                        "question_id": q_arms["id"],
                        "value": arms,
                        "score": 0.8,
                        "agent": AGENT,
                    },
                ).raise_for_status()

        for schema in (chars, outcomes):
            client.post(
                f"/api/v2/schemas/{schema['id']}:rebuild-index"
            ).raise_for_status()

        # A workspace with no schemas at all: drives the grid's empty state in the demo.
        empty_ws = next(
            (w for w in workspaces if w["name"] == EMPTY_WORKSPACE_NAME), None
        )
        if empty_ws is None:
            empty_ws = (
                client.post("/api/v1/workspaces", json={"name": EMPTY_WORKSPACE_NAME})
                .raise_for_status()
                .json()
            )

        projection = (
            client.get("/api/v2/projection", params={"workspace_id": workspace_id})
            .raise_for_status()
            .json()
        )

        out = {
            "workspaceId": workspace_id,
            "emptyWorkspaceId": empty_ws["id"],
            "emptyWorkspaceName": EMPTY_WORKSPACE_NAME,
            "workspaceName": WORKSPACE_NAME,
            "schemas": {
                CHARS_SCHEMA: chars["id"],
                OUTCOMES_SCHEMA: outcomes["id"],
                ROB_SCHEMA: rob["id"],
            },
            "references": [ref for ref, *_ in STUDIES],
            "columns": [c["name"] for c in projection["columns"]],
            "rowCount": len(projection["rows"]),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2))
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
