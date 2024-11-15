---
description: Get started with Extralit in less 10 minutes
---

# Quickstart
>:warning: This page is currently under construction. Please check back later for updates.

Extralit is a free, open-source, self-hosted tool. This means you need to deploy its UI to start using it. There is two main ways to deploy Extralit:

!!! huggingface "Deploy on the Hugging Face Hub"

    The **recommended choice to get started**. You can get up and running in under 5 minutes and don't need to maintain a server or run any commands.

    === "No-code"

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

    


!!! docker "Deploy with Docker"
     If you want to **run Extralit locally on your machine or a server**, or tune the server configuration, choose this option. To use this option, [check this guide](how-to-deploy-argilla-with-docker.md).

## Sign in into the Extralit UI
If everything went well, you should see the Extralit sign in page that looks like this:

![Focus view](../assets/images/getting_started/signin-hf-page.png){ width=100% height=100% }

!!! info "Building errors"
    If you get a build error, sometimes restarting the Space from the Settings page works, otherwise [check the HF Spaces settings guide](how-to-configure-argilla-on-huggingface.md).

In the sign in page:

1. Click on **Sign in with Hugging Face**.

2. **Authorize the application** and you will be logged in into Argilla as an `owner`.

!!! info "Unauthorized error"
    Sometimes, after authorizing you'll see an unauthorized error, and get redirected to the sign in page. Typically, clicking the Sign in button again will solve this issue.

Congrats! Your Argilla server is ready to start your first project using the Python SDK. You now have full rights to create datasets. Follow the instructions in the home page, or keep reading this guide if you want a more detailed explanation.

## Install the Python SDK

To manage workspaces and datasets in Argilla, you need to use the Argilla Python SDK. You can install it with pip as follows:

```console
pip install extralit
```

## Create your first dataset

The quickest way to start exploring the tool and create your first dataset is by importing an exiting one from the Hugging Face Hub.

To do this, log in to the Argilla UI and in the Home page click on "Import from Hub". You can choose one of the sample datasets or paste a repo id in the input. This will look something like `stanfordnlp/imdb`.

Argilla will automatically interpret the columns in the dataset to map them to Fields and Questions.

**Fields** include the data that you want feedback on, like text, chats, or images. If you want to exclude any of the Fields that Argilla identified for you, simply select the "No mapping" option.

**Questions** are the feedback you want to collect, like labels, ratings, rankings, or text. If Argilla identified questions in your dataset that you don't want, you can eliminate them. You can also add questions of your own.

![Screenshot of the dataset configuration page](../assets/images/getting_started/dataset_configurator.png)

Note that you will be able to modify some elements of the configuration of the dataset after it has been created from the Dataset Settings page e.g., the titles of fields and questions. Check all the settings you can modify in the [Update a dataset](../how_to_guides/dataset.md#update-a-dataset) section.

When you're happy with the result, you'll need to give a name to your dataset, select a workspace and choose a split, if applicable. Then, Argilla will start importing the dataset in the background. Now you're all set up to start annotating!

!!! info "Importing long datasets"
    Argilla will only import the first 10k rows of a dataset. If your dataset is larger, you can import the rest of the records at any point using the Python SDK.

    To do that, open your dataset and copy the code snippet provided under "Import data". Now, open a Jupyter or Google Colab notebook and install argilla:

    ```python
    !pip install argilla
    ```
    Then, paste and run your code snippet. This will import the remaining records to your dataset.

## Install and connect the Python SDK

For getting started with Argilla and its SDK, we recommend to use Jupyter Notebook or Google Colab. You will need this to manage users, workspaces and datasets in Argilla.

In your notebook, you can install the Argilla SDK with pip as follows:

```python
!pip install argilla
```

To start interacting with your Argilla server, you need to instantiate a client with an API key and API URL:

- The `<api_key>` is in the `My Settings` page of your Argilla Space but make sure you are logged in with the `owner` account you used to create the Space.

- The `<api_url>` is the URL shown in your browser if it ends with `*.hf.space`.

```python
import argilla as rg

client = rg.client(
    api_url="<api_url>",
    api_key="<api_key>"
)
```

!!! info "You can't find your API URL"
    If you're using Spaces, sometimes the Argilla UI is embedded into the Hub UI so the URL of the browser won't match the API URL. In these scenarios, you have several options:

    1. In the Home page of Argilla, click on "Import from the SDK". You will find your API URL and key in the code snippet provided.
    2. Click on the three points menu at the top of the Space, select "Embed this Space", and open the direct URL.
    3. Use this pattern: `https://[your-owner-name]-[your_space_name].hf.space`.

To check that everything is running correctly, you can call `me`. This should return your user information:

```python
client.me
```

From here, you can manage all of your assets in Argilla, including updating the dataset we created earlier and adding advanced information, such as vectors, metadata or suggestions. To learn how to do this, check our [how to guides](../how_to_guides/index.md).

## Export your dataset to the Hub

Once you've spent some time annotating your dataset in Argilla, you can upload it back to the Hugging Face Hub to share with others or version control it.

To do that, first follow the steps in the previous section to connect to your Argilla server using the SDK. Then, you can load your dataset and export it to the hub like this:

```python
dataset = client.datasets(name="my_dataset")

dataset.to_hub(repo_id="<my_org>/<my_dataset>")
```

For more info on exporting datasets to the Hub, read our guide on [exporting datasets](../how_to_guides/import_export.md#export-to-hub).

## Next steps
- To learn how to create your datasets, workspace, and manage users, check the [how-to guides](../admin_guide/index.md).

- To learn Argilla with hands-on examples, check the [Tutorials section](../tutorials/index.md).

- To further configure your Argilla Space, check the [Hugging Face Spaces settings guide](how-to-configure-argilla-on-huggingface.md).
