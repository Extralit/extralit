---
description: Installation of the Extralit package.
---

# Installation

## Install the Extralit package with pip

```console
pip install extralit
```

## Run the Extralit server

If you have already deployed Extralit server, you can skip this step. Otherwise, you can quickly deploy it in two different ways:

* [Using a HF Space](./how-to-configure-argilla-on-huggingface.md).

* [Locally with Docker](./how-to-deploy-argilla-with-docker.md).


## Connect to the Extralit server

Get your `<api_url>`:

* If you are using HF Spaces, it should be constructed as follows: `https://[your-owner-name]-[your_space_name].hf.space`
* If you are using Docker, it is the URL shown in your browser (by default `http://localhost:6900`)

Get your `<api_key>` in `My Settings` in the Argilla UI (by default owner.apikey).

!!! note
    Make sure to replace `<api_url>` and `<api_key>` with your actual values. If you are using a private HF Space, you need to specify your `HF_TOKEN` which can be found [here](https://huggingface.co/settings/tokens).

```python
import argilla as rg

client = rg.init(
    api_url="<api_url>",
    api_key="<api_key>",
    # headers={"Authorization": f"Bearer {HF_TOKEN}"}
)
```

