---
description: This is a step-by-step guide to help you contribute to the Extralit project. We are excited to have you on board! 🚀
hide:
  - footer
---

# Contributing to Extralit

Thank you for investing your time in contributing to the project! Any contribution you make will be reflected in the most recent version of Extralit 🤩.

??? Question "New to contributing in general?"
    If you're a new contributor, read the [README](https://github.com/extralit/extralit/blob/main/README.md) to get an overview of the project. In addition, here are some resources to help you get started with open-source contributions:

    * **Slack**: You are welcome to join the [Extralit Slack community](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ), where you can keep in touch with other users, contributors and the Extralit team. In the following [section](#first-contact-in-slack), you can find more information on how to get started in Slack.
    * **Git**: This is a very useful tool to keep track of the changes in your files. Using the command-line interface (CLI), you can make your contributions easily. For that, you need to have it [installed and updated](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) on your computer.
    * **GitHub**: It is a platform and cloud-based service that uses git and allows developers to collaborate on projects. To contribute to Extralit, you'll need to create an account. Check the [Contributor Workflow with Git and Github](#contributor-workflow-with-git-and-github) for more info.
    * **Developer Documentation**: To collaborate, you'll need to set up an efficient environment. Check the [developer documentation](developer.md) to know how to do it.

## First Contact in Slack

Slack is our primary communication tool for contributors and users. Click [here](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ) to join the Extralit Slack community.

When you join our Slack workspace, you'll find several channels:

* **#general**: 💬 General development discussions for Extralit developers.
* **#greeting**: 👋 Introduce yourself and say hi to the community.
* **#gsoc-onboarding**: 📣 Important information about GSoC deadlines and program.
* **#gsoc-general**: 💬 General discussions about GSoC.
* **#proj-***: 👩‍💻 Project-specific discussions and development.
* **#help**: 🙋‍♀️ Need assistance? We're always here to help.
* **#news**: 📢 Important updates about Extralit.

So now there is only one thing left to do: introduce yourself and talk to the community. You'll always be welcome! 🤗👋


## Contributor Workflow with Git and GitHub

If you're working with Extralit and suddenly a new idea comes to your mind or you find an issue that can be improved, it's time to actively participate and contribute to the project!

### Report an issue

If you spot a problem, [search if an issue already exists](https://github.com/extralit/extralit/issues?q=is%3Aissue). You can use the `Label` filter. If that is the case, participate in the conversation. If it does not exist, create an issue by clicking on `New Issue`.

This will show various templates, choose the one that best suits your issue.

Below, you can see an example of the `Feature request` template. Once you choose one, you will need to fill in it following the guidelines. Try to be as clear as possible. In addition, you can assign yourself to the issue and add or choose the right labels. Finally, click on `Submit new issue`.


### Work with a fork

#### Fork the Extralit repository

After having reported the issue, you can start working on it. For that, you will need to create a fork of the project. To do that, click on the `Fork` button.

Now, fill in the information. Remember to uncheck the `Copy develop branch only` if you are going to work in or from another branch (for instance, to fix documentation the `main` branch is used). Then, click on `Create fork`.

Now, you will be redirected to your fork. You can see that you are in your fork because the name of the repository will be your `username/extralit`, and it will indicate `forked from extralit/extralit`.


#### Clone your forked repository

In order to make the required adjustments, clone the forked repository to your local machine. Choose the destination folder and run the following command:

```sh
git clone https://github.com/[your-github-username]/extralit.git
cd extralit
```

To keep view changes between Extralit and Argilla, add Argilla as remote upstreams:

```sh
git remote add upstream https://github.com/argilla-io/argilla.git
```


### Create a new branch

For each issue you're addressing, it's advisable to create a new branch. GitHub offers a straightforward method to streamline this process.

> ⚠️ Never work directly on the `main` or `develop` branch. Always create a new branch for your changes.

Navigate to your issue and on the right column, select `Create a branch`.

After the new window pops up, the branch will be named after the issue, include a prefix such as feature/, bug/, or docs/ to facilitate quick recognition of the issue type. In the `Repository destination`, pick your fork ( [your-github-username]/extralit), and then select `Change branch source` to specify the source branch for creating the new one. Complete the process by clicking `Create branch`.

> 🤔 Remember that the `main` branch is only used to work with the documentation. For any other changes, use the `develop` branch.

Now, locally change to the new branch you just created.

```sh
git fetch origin
git checkout [branch-name]
```

### Use CHANGELOG.md

If you are working on a new feature, it is a good practice to make note of it for others to keep up with the changes. For that, we utilize the `CHANGELOG.md` file in the root directory. This file is used to list changes made in each version of the project and there are headers that we use to denote each type of change.

- **Added:** for new features.
- **Changed:** for changes in existing functionality.
- **Deprecated:** for soon-to-be removed features.
- **Removed:** for now removed features.
- **Fixed:** for any bug fixes.
- **Security:** in case of vulnerabilities.

A sample addition would be:

```md
- Fixed the key errors for the `init` method ([#NUMBER_OF_PR](LINK_TO_PR)). Contributed by @github_handle.
```

You can have a look at the CHANGELOG.md file to see more cases and examples.

### Make changes and push them

Make the changes you want in your local repository, and test that everything works and you are following the guidelines.

> Check the [developer documentation](developer.md) to set up your environment and start working on the project.

Once you have finished, you can check the status of your repository and synchronize with the upstreaming repo with the following command:

```sh
# Check the status of your repository
git status

# Synchronize with the upstreaming repo
git checkout [branch-name]
git rebase [default-branch]
```

If everything is right, we need to commit and push the changes to your fork. For that, run the following commands:

```sh
# Add the changes to the staging area
git add filename

# Commit the changes by writing a proper message
git commit -m "commit-message"

# Push the changes to your fork
git push origin [branch-name]
```

When pushing, you will be asked to enter your GitHub login credentials. Once the push is complete, all local commits will be on your GitHub repository.


### Create a pull request

Come back to GitHub, navigate to the original repository where you created your fork, and click on `Compare & pull request`.

First, click on `compare across forks` and select the right repositories and branches.

> In the base repository, keep in mind to select either `main` or `develop` based on the modifications made. In the head repository, indicate your forked repository and the branch corresponding to the issue.

Then, fill in the pull request template. You should add a prefix to the PR name as we did with the branch above. If you are working on a new feature, you can name your PR as `feat: TITLE`. If your PR consists of a solution for a bug, you can name your PR as `bug: TITLE` And, if your work is for improving the documentation, you can name your PR as `docs: TITLE`.

In addition, on the right side, you can select a reviewer (for instance, if you discussed the issue with a member of the Extralit team) and assign the pull request to yourself. It is highly advisable to add labels to PR as well. You can do this again by the labels section right to the screen. For instance, if you are addressing a bug, add the `bug` label or if the PR is related to the documentation, add the `documentation` label. This way, PRs can be easily filtered.

Finally, fill in the template carefully and follow the guidelines. Remember to link the original issue and enable the checkbox to allow maintainer edits so the branch can be updated for a merge. Then, click on `Create pull request`.


### Review your pull request

Once you submit your PR, a team member will review your proposal. We may ask questions, request additional information or ask for changes to be made before a PR can be merged, either using [suggested changes](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/incorporating-feedback-in-your-pull-request) or pull request comments.

You can apply the changes directly through the UI (check the files changed and click on the right-corner three dots) or from your fork, and then commit them to your branch. The PR will be updated automatically and the suggestions will appear as outdated.

> If you run into any merge issues, check out this [git tutorial](https://github.com/skills/resolve-merge-conflicts) to help you resolve merge conflicts and other issues.


### Your PR is merged!

Congratulations 🎉🎊 We thank you 🤩

Once your PR is merged, your contributions will be publicly visible on the [Extralit GitHub](https://github.com/extralit/extralit#contributors).

Additionally, we will include your changes in the next release based on our [development branch](https://github.com/extralit/extralit/tree/develop).

## Additional resources

Here are some helpful resources for your reference.

* [Configuring Slack](https://slack.com/help/categories/360000049063), a guide to learn how to get started with Slack.
* [Pro Git](https://git-scm.com/book/en/v2), a book to learn Git.
* [Git in VSCode](https://code.visualstudio.com/docs/sourcecontrol/overview), a guide to learn how to easily use Git in VSCode.
* [GitHub Skills](https://skills.github.com/), an interactive course to learn GitHub.
