---
description: Get started with Extralit in less 10 minutes
title: quickstart
---
# Quickstart

> :warning: This page is currently under construction. Please check back later for updates.

Extralit is a free, open-source, self-hosted tool. This means you need to deploy its UI to start using it. There is two main ways to deploy Extralit:

!!! huggingface "Deploy on the Hugging Face Hub"

```
The **recommended choice to get started**. You can get up and running in under 5 minutes and don't need to maintain a server or run any commands.

If you're just getting started with Extralit, click the deploy button below:

<div style="margin: 5px">
    <a href="https://huggingface.co/spaces/extralit/public-demo?duplicate=true" target="_blank">
        <img src="https://huggingface.co/datasets/huggingface/badges/raw/main/deploy-to-spaces-lg.svg" />
    </a>
</div>

You can use the default values following these steps:

- Leave the default owner if using your personal account
  - Leave `ADMIN_USERNAME` and `ADMIN_PASSWORD` secrets empty since you'll sign in with your HF user as the Argilla Space `owner`.

- You must fill out the following Space secrets fields:
  - `OAUTH2_HUGGINGFACE_CLIENT_ID` and `OAUTH2_HUGGINGFACE_CLIENT_SECRET`: The Oauth.
  - `ARGILLA_DATABASE_URL`: The URL of the PostgreSQL database where the data will be stored. If you leave it blank, the data will be lost when the Space restarts.
  - `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`: The name of the S3 bucket where papers and data extraction artifacts will be stored. If you leave it blank, the data will be lost when the Space restarts.
- Click Duplicate Space to build an Extralit instance 🚀.
- Once you see the UI, [go to the Sign in into the UI section](#sign-in-into-the-argilla-ui). If you see the `Building` message for longer than 2-3 min refresh the page.


!!! warning "Database persistent storage"
    Not setting the `ARGILLA_DATABASE_URL` Space secret that **you will loose your data when the Space restarts**. Spaces get restarted due to maintainance, inactivity, and every time you change your Spaces settings. If you want to **use the Space just for testing** you can leave it blank temporarily.

If you want to deploy Extralit within a Hugging Face organization, setup a more stable Space, or understand the settings, [check out the HF Spaces settings guide](how-to-configure-argilla-on-huggingface.md).

- Setting up HF Authentication

    From version `1.23.0` you can enable Hugging Face authentication for your Extralit Space. This feature allows you to give access to your Extralit Space to users that are logged in to the Hugging Face Hub.

    >
    This feature is specially useful for public crowdsourcing projects. If you would like to have more control over who can log in to the Space, you can set this up on a private space so that only members of your Organization can sign in. Alternatively, you may want to [create users](/getting_started/installation/configurations/user_management.md#create-a-user) and use their credentials instead.

    To enable this feature, you will first need to [create an OAuth App in Hugging Face](https://huggingface.co/docs/hub/oauth#creating-an-oauth-app). To do that, go to your user settings in Hugging Face and select *Connected Apps* > *Create App*. Once inside, choose a name for your app and complete the form with the following information:

    * **Homepage URL:** [Your Extralit Space Direct URL](/getting_started/installation/deployments/huggingface-spaces.md#your-argilla-space-url).
    * **Logo URL:** `[Your Extralit Space Direct URL]/favicon.ico`
    * **Scopes:** `openid` and `profile`.
    * **Redirect URL:** `[Your Extralit Space Direct URL]/oauth/huggingface/callback`

    This will create a Client ID and an App Secret that you will need to add as variables of your Space. To do this, go to the Space *Settings* > *Variables and Secrets* and save the Client ID and App Secret as environment secrets like so:

    1. **Name:** `OAUTH2_HUGGINGFACE_CLIENT_ID` - **Value:** [Your Client ID]
    2. **Name:** `OAUTH2_HUGGINGFACE_CLIENT_SECRET` - **Value:** [Your App Secret]
```

!!! docker "Deploy with Docker" If you want to **run Extralit locally on your machine or a server**, or tune the server configuration, choose this option. To use this option, [check this guide](how-to-deploy-argilla-with-docker.md).

## Sign in into the Extralit UI

If everything went well, you should see the Extralit sign in page that looks like this:

![Focus view](/argilla/docs/assets/images/getting_started/signin-hf-page.png){ width=100% height=100% }

!!! info "Building errors" If you get a build error, sometimes restarting the Space from the Settings page works, otherwise [check the HF Spaces settings guide](how-to-configure-argilla-on-huggingface.md).

In the sign in page:

1. Click on **Sign in with Hugging Face**
2. **Authorize the application** and you will be logged in into Argilla as an `owner`.

!!! info "Unauthorized error" Sometimes, after authorizing you'll see an unauthorized error, and get redirected to the sign in page. Typically, clicking the Sign in button solves the issue.

Congrats! Your Argilla server is ready to start your first project using the Python SDK. You now have full rights to create datasets. Follow the instructions in the home page, or keep reading this guide if you want a more detailed explanation.

## Install the Python SDK

To manage workspaces and datasets in Argilla, you need to use the Argilla Python SDK. You can install it with pip as follows:

```console
pip install extralit
```

## Create your first dataset

For getting started with Argilla and its SDK, we recommend to use Jupyter Notebook or Google Colab.

To start interacting with your Argilla server, you need to create a instantiate a client with an API key and API URL:

- The `<api_key>` is in the `My Settings` page of your Argilla Space.

- The `<api_url>` is the URL shown in your browser if it ends with `*.hf.space`.

```python
import argilla as rg

client = rg.client(
    api_url="<api_url>",
    api_key="<api_key>"
)
```

!!! info "You can't find your API URL" If you're using Spaces, sometimes the Argilla UI is embedded into the Hub UI so the URL of the browser won't match the API URL. In these scenarios, there are two options: 1. Click on the three points menu at the top of the Space, select "Embed this Space", and open the direct URL. 2. Use this pattern: `https://[your-owner-name]-[your_space_name].hf.space`.

To create a dataset with a simple text classification task, first, you need to **define the dataset settings**.

```python
settings = rg.Settings(
    guidelines="Classify the reviews as positive or negative.",
    fields=[
        rg.TextField(
            name="review",
            title="Text from the review",
            use_markdown=False,
        ),
    ],
    questions=[
        rg.LabelQuestion(
            name="my_label",
            title="In which category does this article fit?",
            labels=["positive", "negative"],
        )
    ],
)
```

Now you can **create the dataset with these settings**. Publish the dataset to make it available in the UI and add the records.

!!! info "About workspaces" Workspaces in Argilla group datasets and user access rights. The `workspace` parameter is optional in this case. If you don't specify it, the dataset will be created in the default workspace `argilla`.

```
By default, **this workspace will be visible to users joining with the Sign in with Hugging Face button**. You can create other workspaces and decide to grant access to users either with the SDK or the [changing the OAuth configuration](how-to-configure-argilla-on-huggingface.md).
```

```python
dataset = rg.Dataset(
    name=f"my_first_dataset",
    settings=settings,
    client=client,
    #workspace="argilla"
)
dataset.create()
```

Now you can **add records to your dataset**. We will use the IMDB dataset from the Hugging Face Datasets library as an example. The `mapping` parameter indicates which keys/columns in the source dataset correspond to the Argilla dataset fields.

```python
from datasets import load_dataset

data = load_dataset("imdb", split="train[:100]").to_list()

dataset.records.log(records=data, mapping={"text": "review"})
```

🎉 You have successfully created your first dataset with Argilla. You can now access it in the Argilla UI and start annotating the records.

## Next steps

- To learn how to create your datasets, workspace, and manage users, check the <SwmLink doc-title="index" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/index.99rb6ksv.sw.md">[index](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/99rb6ksv)</SwmLink>.

- To learn Argilla with hands-on examples, check the <SwmLink doc-title="index" repo-id="Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA==" repo-name="extralit" path="/.swm/index.oqcx0ht1.sw.md">[index](https://app.swimm.io/repos/Z2l0aHViJTNBJTNBZXh0cmFsaXQlM0ElM0FleHRyYWxpdA%3D%3D/docs/oqcx0ht1)</SwmLink>.

- To further configure your Argilla Space, check the [Hugging Face Spaces settings guide](how-to-configure-argilla-on-huggingface.md).

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
