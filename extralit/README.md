<h1 align="center">
  <a href=""><img src="https://github.com/extralit/extralit/raw/develop/argilla/docs/assets/logo.svg" alt="Extralit" width="150"></a>
  <br>
  Extralit
  <br>
</h1>
<h3 align="center">Extract structured data from scientific literature with human validation</h2>

<p align="center">
<a href="https://pypi.org/project/extralit/">
<img alt="CI" src="https://img.shields.io/pypi/v/extralit.svg?style=flat-round&logo=pypi&logoColor=white">
</a>
<img alt="Codecov" src="https://codecov.io/gh/extralit/extralit/branch/main/graph/badge.svg"/>
<a href="https://pepy.tech/project/extralit">
<img alt="Downloads" src="https://static.pepy.tech/personalized-badge/extralit?period=month&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads/month">
</a>
</p>

<p align="center">
<a href="https://twitter.com/extralit_ai">
<img src="https://img.shields.io/badge/twitter-black?logo=x"/>
</a>
<a href="https://www.linkedin.com/company/extralit-ai">
<img src="https://img.shields.io/badge/linkedin-blue?logo=linkedin"/>
</a>
<a href="https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ">
<img src="https://img.shields.io/badge/Slack-4A154B?&logo=slack&logoColor=white"/>
</a>
</p>

Extralit is an open-source platform that transforms how researchers extract structured data from scientific literature. Want to get started? Check out our [documentation](https://docs.extralit.ai/latest/).

## Why use Extralit?

### Accelerate Scientific Data Collection

Manual data extraction from research papers is slow and error-prone, often taking 6-12 months for systematic reviews. Extralit combines AI-powered extraction with human validation to reduce this to weeks while maintaining research-grade accuracy.

### Take Control of Your Research Data

Most scientific data extraction tools are inflexible black boxes. Extralit is different - it's open source and puts you in control. Define custom extraction schemas, validate results, and integrate with your existing research workflows.

### Scale Your Literature Reviews

Whether you're conducting a systematic review, meta-analysis, or building a scientific knowledge base, Extralit helps you efficiently process hundreds of papers. Our platform handles complex tables, figures, and relationships while preserving scientific rigor.

## 🏘️ Community

We're an open-source project built for researchers, by researchers. Here's how to get involved:

- [Slack Community](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ): Connect with other researchers and developers
- [Documentation](https://docs.extralit.ai): Learn how to use and contribute to Extralit
- [Roadmap](https://github.com/orgs/extralit/projects/1/views/1): See what we're building and share your ideas

## Real-World Impact

Extralit is already accelerating research at leading institutions:

- **Gates Foundation**: Reduced systematic review time for malaria intervention studies from 6 months to 6 weeks
- **Life Science Research**: Streamlined extraction of clinical trial endpoints, genetic markers, and intervention protocols
- **Meta-Analysis**: Enabled rapid synthesis of evidence across hundreds of papers while maintaining rigorous validation

## 👨‍💻 Getting Started

### Installation

Install Extralit using pip:

```console
pip install extralit
```

Initialize the client:

```python
import extralit as ex

client = ex.Extralit(
    api_url="https://your-deployment-url", 
    api_key="your-api-key"
)
```

### Create an extraction schema

Define what data you want to extract:

```python
schema = ex.Schema(
    name="clinical_trial",
    fields=[
        ex.TextField(name="intervention", required=True),
        ex.NumericField(name="sample_size", required=True),
        ex.TextField(name="outcome_measure"),
        ex.TableField(name="results_table")
    ]
)

project = client.create_project(
    name="trial_extraction",
    schema=schema
)
```

### Add documents and start extraction

```python
# Add PDFs to extract from
project.add_documents("path/to/papers/*.pdf")

# Start extraction
extractions = project.extract()

# Review and validate results
validated_data = project.validate(extractions)
```

Need more help? Check out our [detailed tutorials](https://docs.extralit.ai/latest/tutorials).

## 🥇 Contributors

Want to contribute? Great! Check out our [contribution guide](https://docs.extralit.ai/latest/community/contributor) or join our [Slack community](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ).

<a href="https://github.com/extralit/extralit/graphs/contributors">
<img src="https://contrib.rocks/image?repo=extralit/extralit" />
</a>
