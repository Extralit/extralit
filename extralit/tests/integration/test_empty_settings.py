import random
from string import ascii_lowercase

import pytest

from extralit import Dataset, Extralit, Settings, TextField, TextQuestion, Workspace
from extralit._exceptions import SettingsError


def test_dataset_empty_settings(client: Extralit, workspace: Workspace):
    name = "".join(random.choices(ascii_lowercase, k=16))
    settings = Settings()
    dataset = Dataset(
        name=name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )
    with pytest.raises(expected_exception=SettingsError):
        dataset.create()


def test_dataset_no_fields(client: Extralit, workspace: Workspace) -> None:
    name = "".join(random.choices(ascii_lowercase, k=16))
    settings = Settings(
        questions=[
            TextQuestion(name="text_question"),
        ],
    )
    dataset = Dataset(
        name=name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )
    with pytest.raises(expected_exception=SettingsError):
        dataset.create()


def test_dataset_no_questions(client: Extralit, workspace: Workspace) -> Dataset:
    name = "".join(random.choices(ascii_lowercase, k=16))
    settings = Settings(
        fields=[
            TextField(name="text_field"),
        ],
    )
    dataset = Dataset(
        name=name,
        workspace=workspace.name,
        settings=settings,
        client=client,
    )
    with pytest.raises(expected_exception=SettingsError):
        dataset.create()
