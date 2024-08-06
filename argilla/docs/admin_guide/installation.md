
---
description: Installation of the Extralit package.
---

## Developer documentation

If you want to contribute to the development of the SDK, you can follow the instructions below.

### Installation

To install the development dependencies, run the following commands:

```console
# Install pdm (https://github.com/pdm-project/pdm)
pip install pdm

# Install the package in editable mode
pip install -e .

# Install the development dependencies with pdm
pdm install --dev
```

### Generating documentation

To generate the docs you will need to install the development dependencies, and run the following command to create the development server with `mkdocs`:

```console
mkdocs serve
```

You will find the built documentation in `http://localhost:8000/argilla-python/`.
