from extralit import (
    Dataset,
    Extralit,
    FloatMetadataProperty,
    IntegerMetadataProperty,
    LabelQuestion,
    MultiLabelQuestion,
    RankingQuestion,
    RatingQuestion,
    Settings,
    SpanQuestion,
    TermsMetadataProperty,
    TextField,
    TextQuestion,
    Workspace,
)


def test_publish_dataset(client: "Extralit", dataset_name: str):
    ws_name = "new-ws"

    new_ws = client.workspaces(ws_name) or Workspace(name=ws_name).create()
    assert client.api.workspaces.exists(new_ws.id), "The workspace was not created"

    ds = client.datasets(dataset_name, workspace=new_ws)
    if ds:
        ds.delete()
        assert not client.api.datasets.exists(ds.id), "The dataset was not deleted"

    ds = Dataset(name=dataset_name, workspace=new_ws)

    ds.settings = Settings(
        guidelines="This is a test dataset",
        allow_extra_metadata=True,
        fields=[TextField(name="text-field")],
        questions=[
            TextQuestion(name="text-question"),
            RatingQuestion(name="rating-question", values=[1, 2, 3, 4, 5]),
            RankingQuestion(name="ranking-question", values=["rank1", "rank2", "rank3"]),
            LabelQuestion(name="label-question", labels=["A", "B", "C"]),
            MultiLabelQuestion(name="multi-label-question", labels=["A", "B", "C"]),
            SpanQuestion(name="span-question", field="text-field", labels=["label1", "label2"]),
        ],
        metadata=[
            TermsMetadataProperty(name="metadata-property", options=["term1", "term2"]),
            TermsMetadataProperty(name="term-property"),
            IntegerMetadataProperty(name="metadata-property-2", min=0, max=10),
            FloatMetadataProperty(name="metadata-property-3", min=0, max=10),
        ],
    )

    ds.create()

    created_dataset = client.datasets(name=ds.name, workspace=new_ws)
    assert client.api.datasets.exists(created_dataset.id), "The dataset was not found"
    assert created_dataset == ds
    assert created_dataset.settings == ds.settings, "The settings were not saved"

    assert created_dataset.guidelines == ds.guidelines
    assert created_dataset.allow_extra_metadata == ds.allow_extra_metadata
    assert created_dataset.fields == ds.fields
    assert created_dataset.questions == ds.questions
    assert created_dataset.schema == ds.schema
