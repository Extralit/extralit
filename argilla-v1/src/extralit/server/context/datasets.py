import os
from typing import Optional

import argilla as rg
from argilla.client.feedback.dataset.remote.dataset import RemoteFeedbackDataset
from argilla.client.sdk.commons.errors import UnauthorizedApiError


def get_argilla_dataset(dataset_name="Table-Preprocessing", workspace_name="itn-recalibration") -> RemoteFeedbackDataset:
    try:
        rg.init(
            api_url=os.getenv('ARGILLA_BASE_URL'),
            api_key=os.getenv('ARGILLA_API_KEY'),
            workspace='argilla',
        )
    except Exception as e:
        print(e)

    dataset = rg.FeedbackDataset.from_argilla(name=dataset_name, workspace=workspace_name, with_documents=False)

    return dataset
