
<h1 align="center">
  <a href=""><img src="https://github.com/extralit/extralit/blob/develop/argilla/docs/assets/logo.png" alt="Extralit" width="500"></a>
</h1>

<h3>
<p align="center">
<a href="https://docs.extralit.ai/latest/" target="_blank">📄 Documentation</a> | </span>
<a href="https://docs.extralit.ai/latest/getting_started/quickstart/" target="_blank">🚀 Quickstart</a> <span> | </span>
<a href="https://docs.extralit.ai/latest/community/developer/" target="_blank">🛠️ Architecture</a> <span>
</p>
</h3>

## What is Extralit?

Extralit (EXTRAct LITerature) is a data extraction workflow with user-friendly UI, designed for **LLM-assisted scientific data extraction** and other **unstructured document intelligence** tasks. It focuses on data accuracy above all else, and further integrates human feedback loops for continuous LLM refinement and collaborative data extraction.

- 🔹 Precision First – Built for high data accuracy, ensuring reliable results.
- 🔹 Human-in-the-Loop – Seamlessly integrate human annotations to refine LLM outputs and collaborate on data validation.
- 🔹 Flexible & Scalable – Available as a Python SDK, CLI, and Web UI with multiple deployment options to fit your workflow.

🌟 Key Features

- ✅ Schema-Driven Extraction – Define structured schemas for context-aware, high-accuracy data extraction across scientific domains.
- ✅ Advanced PDF Processing – AI-powered OCR detects complex table structures in both digital and scanned PDFs.
- ✅ Built-in Validation – Automatically verify extracted data for accuracy in both the annotation UI and the data pipeline outputs.
- ✅ User-Friendly Interface – Easily review, edit, and validate data with team-based consensus workflows.
- ✅ Data Flywheel – Collect human annotations to monitor performance and build fine-tuning datasets for continuous improvement.

Start extracting smarter with Extralit! 🚀

<<<<<<< HEAD
## Getting started
=======
Argilla can be used for collecting human feedback for a wide variety of AI projects like traditional NLP (text classification, NER, etc.), LLMs (RAG, preference tuning, etc.), or multimodal models (text to image, etc.). Argilla's programmatic approach lets you build workflows for continuous evaluation and model improvement. The goal of Argilla is to ensure your data work pays off by quickly iterating on the right data and models.

### Improve your AI output quality through data quality

Compute is expensive and output quality is important. We help you focus on data, which tackles the root cause of both of these problems at once. Argilla helps you to **achieve and keep high-quality standards** for your data. This means you can improve the quality of your AI output.

### Take control of your data and models

Most AI tools are black boxes. Argilla is different. We believe that you should be the owner of both your data and your models. That's why we provide you with all the tools your team needs to **manage your data and models in a way that suits you best**.

### Improve efficiency by quickly iterating on the right data and models

Gathering data is a time-consuming process. Argilla helps by providing a tool that allows you to **interact with your data in a more engaging way**. This means you can quickly and easily label your data with filters, AI feedback suggestions and semantic search. So you can focus on training your models and monitoring their performance.

## 🏘️ Community

We are an open-source community-driven project and we love to hear from you. Here are some ways to get involved:

- [Community Meetup](https://lu.ma/embed-checkout/evt-IQtRiSuXZCIW6FB): listen in or present during one of our bi-weekly events.

- [Discord](http://hf.co/join/discord): get direct support from the community in #argilla-distilabel-general and #argilla-distilabel-help.

- [Roadmap](https://github.com/orgs/argilla-io/projects/10/views/1): plans change but we love to discuss those with our community so feel encouraged to participate.

## What do people build with Argilla?

### Open-source datasets and models

The community uses Argilla to create amazing open-source [datasets](https://huggingface.co/datasets?library=library:argilla&sort=trending) and [models](https://huggingface.co/models?other=distilabel).

- [Cleaned UltraFeedback dataset](https://huggingface.co/datasets/argilla/ultrafeedback-binarized-preferences-cleaned) used to fine-tune the [Notus](https://huggingface.co/argilla/notus-7b-v1) and [Notux](https://huggingface.co/argilla/notux-8x7b-v1) models. The original UltraFeedback dataset was curated using Argilla UI filters to find and report a bug in the original data generation code. Based on this data curation process, Argilla built this new version of the UltraFeedback dataset and fine-tuned Notus, outperforming Zephyr on several benchmarks.
- [distilabel Intel Orca DPO dataset](https://huggingface.co/datasets/argilla/distilabel-intel-orca-dpo-pairs) used to fine-tune the [improved OpenHermes model](https://huggingface.co/argilla/distilabeled-OpenHermes-2.5-Mistral-7B). This dataset was built by combining human curation in Argilla with AI feedback from distilabel, leading to an improved version of the Intel Orca dataset and outperforming models fine-tuned on the original dataset.

### Examples Use cases

AI teams from organizations such as the [Red Cross](https://510.global/), [Loris.ai](https://loris.ai/) and [Prolific](https://www.prolific.com/) use Argilla to improve the quality and efficiency of AI projects. They shared their experiences in our [AI community meetup](https://lu.ma/embed-checkout/evt-IQtRiSuXZCIW6FB).

- AI for good: [the Red Cross presentation](https://youtu.be/ZsCqrAhzkFU?feature=shared) showcases how the Red Cross domain experts and AI team collaborated by classifying and redirecting requests from refugees of the Ukrainian crisis to streamline the support processes of the Red Cross.
- Customer support: during [the Loris meetup](https://youtu.be/jWrtgf2w4VU?feature=shared) they showed how their AI team uses unsupervised and few-shot contrastive learning to help them quickly validate and gain labeled samples for a huge amount of multi-label classifiers.
- Research studies: [the showcase from Prolific](https://youtu.be/ePDlhIxnuAs?feature=shared) announced their integration with our platform. They use it to actively distribute data collection projects among their annotating workforce. This allows Prolific to quickly and efficiently collect high-quality data for research studies.

## 👨‍💻 Getting started
>>>>>>> v2.6.0

### Installation
Install the client package

```bash
pip install extralit
```

If you already have a server deployed and login credentials, obtain your API key in the User Settings. You can manage your extraction workspace through the CLI with:

```base
extralit login --api-url http://<extralit_server_instance>
# You will be prompted an API key to login to your account
```

### Server setup

See [https://docs.extralit.ai/latest/getting_started/quickstart/](https://docs.extralit.ai/latest/getting_started/quickstart/)

## 🛠️ Project Architecture

Extralit is built on top of Argilla, extending its capabilities with enhanced data extraction, validation, and human-in-the-loop workflows, with these 5 core components:

- **Python SDK**: A Python SDK which is installable with `pip install extralit` to interact with the web server and provides an API to manage the data extraction workflows.
- **FastAPI Server**: The backbone of Argilla, handling users, storage, and API interactions. It manages application data using a relational database (PostgreSQL by default).
- **Web UI**: A web application to visualize and annotate your data, users and teams. It is built with *Vue.js* and *Nuxt.js* and is directly deployed alongside the FastAPI Server within our Docker image.
- **Vector Database**: A vector database to store the records data and perform scalable vector similarity searches and basic document searches. We currently support *ElasticSearch* and *AWS OpenSearch* and they can be deployed as separate Docker images.

## Repo Activity

![Alt](https://repobeats.axiom.co/api/embed/503055f15ba7ac2f51d697153f7c146ae81c6c04.svg "Repobeats analytics image")

