---
description: Installation of the Extralit package.
title: installation
---
# Installation

## Install the Extralit package with pip

```console
pip install extralit
```

## Run the Extralit server

If you have already deployed Extralit server, you can skip this step. Otherwise, you can quickly deploy it in two different ways:

- <SwmLink doc-title="Hugging Face Spaces Settings" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/hugging-face-spaces-settings.83tqipri.sw.md">[Hugging Face Spaces Settings](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/83tqipri)</SwmLink>.

- <SwmLink doc-title="how-to-deploy-argilla-with-docker" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/how-to-deploy-argilla-with-docker.kudvakh0.sw.md">[how-to-deploy-argilla-with-docker](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/kudvakh0)</SwmLink>.

## Connect to the Extralit server

Get your `<api_url>`:

- If you are using HF Spaces, it should be constructed as follows: `https://[your-owner-name]-[your_space_name].hf.space`
- If you are using Docker, it is the URL shown in your browser (by default `http://localhost:6900`)

Get your `<api_key>` in `My Settings` in the Argilla UI (by default owner.apikey).

!!! note Make sure to replace `<api_url>` and `<api_key>` with your actual values. If you are using a private HF Space, you need to specify your `HF_TOKEN` which can be found [here](https://huggingface.co/settings/tokens).

```python
import argilla as rg

client = rg.init(
    api_url="<api_url>",
    api_key="<api_key>",
    # headers={"Authorization": f"Bearer {HF_TOKEN}"}
)
```

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
