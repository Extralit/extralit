import pytest

import extralit as ex


@pytest.fixture
def dataset(client: ex.Extralit, dataset_name: str):
    ws = client.workspaces.default
    settings = ex.Settings(
        guidelines="The dataset guidelines",
        fields=[ex.TextField(name="text", required=True, title="Text")],
        questions=[
            ex.LabelQuestion(name="label", title="Label", labels=["positive", "negative"]),
            ex.RankingQuestion(name="ranking", title="Ranking", values=["1", "2", "3"]),
        ],
    )

    ds = ex.Dataset(
        name=dataset_name,
        settings=settings,
        client=client,
        workspace=ws,
    )
    ds.create()
    yield ds
    ds.delete()


def test_ranking_question_with_suggestions(dataset: ex.Dataset):
    dataset.records.log(
        [
            {"text": "This is a test text", "label": "positive", "ranking": ["2", "1", "3"]},
        ],
    )
    assert next(iter(dataset.records(with_suggestions=True))).suggestions["ranking"].value == ["2", "1", "3"]


def test_ranking_question_with_responses(dataset: ex.Dataset):
    dataset.records.log(
        [
            {"text": "This is a test text", "label": "positive", "ranking_": ["2"]},
        ],
        mapping={"ranking_": "ranking.response"},
    )
    assert next(iter(dataset.records(with_responses=True))).responses["ranking"][0].value == ["2"]
