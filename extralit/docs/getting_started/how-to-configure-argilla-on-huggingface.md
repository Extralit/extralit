---
description: Configure Extralit on Hugging Face Spaces
title: Hugging Face Spaces Settings
---

>:warning: This page is currently under construction. Please check back later for updates.

This section details how to configure and deploy Extralit on Hugging Face Spaces. It covers:

- How to configure persistent storage and database services
- How to configure Extralit
- How to deploy Extralit under a Hugging Face Organization
- How to configure and enable HF OAuth access
- How to use Private Spaces

!!! tip "Looking to get started easily or deploy Extralit with the Python SDK?"
    If you just discovered Extralit and want to get started quickly, go to the [Quickstart guide](quickstart.md).

## Persistent storage

In the Space creation UI, persistent storage is set to `Small PAID`, which is a paid service, charged per hour of usage.

**Spaces get restarted due to maintainance, inactivity, and every time you change your Spaces settings**. Persistent storage enables Extralit to save to disk your datasets and configurations across restarts.

!!! warning "Ephimeral FREE persistent storage"
    Not setting persistent storage to `Small` means that **you will loose your data when the Space restarts**.

    If you plan to **use the Extralit Space beyond testing**, it's highly recommended to **set persistent storage to `Small`**.

If you just want to quickly test or use Extralit for a few hours with the risk of loosing your datasets, choose `Ephemeral FREE`. `Ephemeral FREE` means your datasets and configuration will not be saved to disk, when the Space is restarted your datasets, workspaces, and users will be lost.

If you want to disable the persistence storage warning, you can set the environment variable `EXTRALIT_SHOW_HUGGINGFACE_SPACE_PERSISTENT_STORAGE_WARNING=false`

!!! warning "Read this if you have datasets and want to enable persistent storage"
    If you want to enable persistent storage `Small PAID` and you have created datasets, users, or workspaces, follow this process:

    - First, **make a local or remote copy of your datasets**, following the [Import and Export guide](../admin_guide/import_export.md). This is the most important step, because changing the settings of your Space leads to a restart and thus a data loss.
    - If you have created users (not signed in with Hugging Face login), **consider storing a copy of users** following the [manage users guide](../admin_guide/user.md).
    - **Once you have stored all your data safely, go to you Space Settings Tab** and select `Small`.
    - **Your Space will be restarted and existing data will be lost**. From now on, all the new data you create in Extralit will be kept safely
    - **Recover your data**, by following the above mentioned guides.

## How to configure and disable OAuth access

By default, Extralit Spaces are configured with Hugging Face OAuth, in the following way:

- Any Hugging Face user that can see your Space, can use the Sign in button, join as an `annotator`, and contribute to the datasets available under the `extralit` workspace. This workspace is created during the deployment process.
- These users can only explore and annotate datasets in the `extralit` workspace but can't perform any critical operation like create, delete, update, or configure datasets. By default, any other workspace you create, won't be visible to these users.

To restrict access or change the default behaviour, there's two options:

**Set your Space to private**. This is especially useful if your Space is under an organization. This will **only allow members within your organization to see and join your Extralit space**. It can also be used for personal, solo projects.

**Modify the `.oauth.yml` configuration file**. You can find and modify this file under the `Files` tab of your Space. The default file looks like this:

```yaml

providers:
  - name: huggingface

# Allowed workspaces must exists
allowed_workspaces:
  - name: extralit
```
You can:

- Change the list of `allowed` workspaces.
- Rename the `.oauth.yml` file to disable OAuth access.

For example if you want to let users join a new workspace `community-initiative`:

```yaml
allowed_workspaces:
  - name: extralit
  - name: community-initiative
```

## How to deploy Extralit under a Hugging Face Organization

Creating an Extralit Space within an organization is useful for several scenarios:

- **You want to only enable members of your organization to join your Space**. You can achieve this by setting your Space to private.
- **You want manage the Space together with other users** (e.g., Space settings, etc.). Note that if you just want to manage your Extralit datasets, workspaces, you can achieve this by adding other Extralit `owner` roles to your Extralit Server.
- **More generally, you want to make available your space under an organization/community umbrella**.

The steps are very similar the [Quickstart guide](quickstart.md) with one important difference:

!!! tip "Enable Persistent Storage `SMALL`"
    Not setting persistent storage to `Small` means that **you will loose your data when the Space restarts**.

    For Extralit Spaces with many users, it's strongly recommended to **set persistent storage to `Small`**.

## How to use Private Spaces

Setting your Space visibility to private can be useful if:

- You want to work on your personal, solo project.
- You want your Extralit to be available only to members of the organization where you deploy the Extralit Space.

You can set the visibility of the Space during the Space creation process or afterwards under the `Settings` Tab.

To use the Python SDK with private Spaces you need to specify your `HF_TOKEN` which can be found [here](https://huggingface.co/settings/tokens), when creating the client:

```python
import extralit as ex

HF_TOKEN = "..."

client = ex.Extralit(
    api_url="<api_url>",
    api_key="<api_key>",
    headers={"Authorization": f"Bearer {HF_TOKEN}"}
)
```

## Space Secrets overview

There's two optional secrets to set up the `USERNAME` and `PASSWORD` of the `owner` of the Extralit Space. Remember that, by default Extralit Spaces are configured with a *Sign in with Hugging Face* button, which is also used to grant an `owner` to the creator of the Space for personal spaces.

The `USERNAME` and `PASSWORD` are only useful in a couple of scenarios:

- You have [disabled Hugging Face OAuth](#how-to-configure-and-disable-oauth-access).
- You want to [set up Extralit under an organization](#how-to-deploy-extralit-under-a-hugging-face-organization) and want your Hugging Face username to be granted the `owner` role.

In summary, when setting up a Space:
!!! info "Creating a Space under your personal account"
    If you are creating the Space under your personal account, **don't insert any value for `USERNAME` and `PASSWORD`**. Once you launch the Space you will be able to Sign in with your Hugging Face username and the `owner` role.

!!! info "Creating a Space under an organization"
    If you are creating the Space under an organization **make sure to insert your Hugging Face username in the secret `USERNAME`**. In this way, you'll be able to Sign in with your Hugging Face user.
