# Command Line Interface Guide

This guide explains how to use Extralit's command line interface (CLI) to manage your data extraction projects. The CLI provides tools for every step of the extraction workflow, from setting up projects to exporting final data.

## Getting Started

### Installation

Install Extralit and its CLI using pip:

```bash
pip install extralit
```

For specific features, you can install additional dependencies:
```bash
# For OCR and PDF processing
pip install "extralit-server[ocr,pdf]"

# For LLM-based extraction
pip install "extralit-server[llm]"
```

### Authentication

Before using Extralit, authenticate with your server:

```bash
extralit login --api-url http://your-extralit-server --api-key your-api-key
```

You can verify your authentication status:
```bash
extralit whoami
```

To log out:
```bash
extralit logout
```

### Environment Setup

The CLI uses these environment variables:
- `ARGILLA_API_URL`: Your Extralit server URL
- `ARGILLA_API_KEY`: Your API key

Configuration is stored in `~/.extralit/credentials.json`.

### Shell Completion

Enable command completion for easier CLI use:

```bash
extralit --install-completion
```

After restarting your shell, press `[Tab][Tab]` after typing `extralit` for command suggestions.

## Project Setup and Management

### Creating a Workspace

Start by creating a workspace to organize your extraction project:

```bash
extralit workspaces create --name my-workspace --description "Description of your extraction project"
```

### Managing Team Access

Add team members to collaborate on the project:

```bash
# Add a user with annotator role
extralit workspaces --name my-workspace add-user --username user1 --role annotator

# Remove a user if needed
extralit workspaces --name my-workspace delete-user --username user1
```

### Viewing Available Workspaces

List all workspaces you have access to:

```bash
extralit workspaces list
```

## Document Management

### Importing Documents

Add scientific papers to your workspace:

```bash
extralit documents import --workspace my-workspace \
  --papers path/to/references.csv \
  --metadatas title,authors,year
```

The references CSV should include:
- `reference` (required): Paper ID (e.g., `author_year_firstword`)
- `pmid` (optional): PubMed ID
- `doi` (optional): DOI
- `file_path` (required): Path to PDF file
- `title`, `authors`, `year` (optional): Metadata fields

### Managing Documents

List documents in your workspace:
```bash
extralit documents list --workspace my-workspace
```

Add individual documents:
```bash
extralit documents add --workspace my-workspace \
  [--file paper.pdf] [--url https://...] \
  [--pmid 123456] [--doi 10.1234/...]
```

Delete a document:
```bash
extralit documents delete <document_id> --workspace my-workspace --force
```

## Schema Management

Schemas define the structure of data to be extracted from papers. They specify fields, relationships, and validation rules.

### Managing Schemas

Upload schemas to your workspace:
```bash
extralit schemas upload ./schemas --workspace my-workspace --overwrite
```

Download existing schemas:
```bash
extralit schemas download ./downloaded_schemas \
  --workspace my-workspace \
  [--name specific-schema] \
  [--exclude schema1,schema2]
```

List available schemas:
```bash
extralit schemas list --workspace my-workspace
```

## Extraction Workflow

### 1. PDF Preprocessing

Process PDFs to extract text and detect tables:

```bash
extralit preprocessing run \
  --workspace my-workspace \
  --references ref1,ref2 \
  --text-ocr model1,model2 \
  --table-ocr model1,model2 \
  --output-dataset preprocessing-results
```

### 2. LLM-Based Extraction

Extract structured data using LLMs:

```bash
extralit extraction run \
  --workspace my-workspace \
  --references ref1,ref2 \
  --output-dataset extraction-results
```

### 3. Monitor Progress

Check extraction status:

```bash
extralit extraction status \
  --workspace my-workspace \
  --references ref1,ref2
```

### 4. Export Results

Export extracted data:

```bash
extralit extraction export \
  --workspace my-workspace \
  --output extracted_data.csv
```

## Dataset Operations

### Managing Datasets

Create a new dataset:
```bash
extralit datasets --workspace my-workspace create \
  --name my-dataset \
  --description "Dataset description"
```

List datasets:
```bash
extralit datasets --workspace my-workspace list
```

Delete a dataset:
```bash
extralit datasets --workspace my-workspace delete --name my-dataset
```

### Sharing Datasets

Push to HuggingFace Hub:
```bash
extralit datasets --workspace my-workspace push-to-hub \
  --name my-dataset \
  --repo-id username/repo-name
```

## File Management

### Managing Files

List files:
```bash
extralit files list --workspace my-workspace [--path documents/]
```

Upload files:
```bash
extralit files upload data.csv \
  --workspace my-workspace \
  --remote-path data/data.csv
```

Download files:
```bash
extralit files download data/data.csv \
  --workspace my-workspace \
  --output ./local_data.csv
```

Delete files:
```bash
extralit files delete data/data.csv --workspace my-workspace --force
```

## User Management

### Managing Users

List users:
```bash
extralit users list
```

Create a new user:
```bash
extralit users create \
  --username user1 \
  --password password123 \
  --full-name "User One" \
  --email user1@example.com
```

Delete a user:
```bash
extralit users delete --username user1
```

## Training Models

Train extraction models:

```bash
# Basic training
extralit training --name my-dataset --framework spacy --model en_core_web_sm

# Advanced options
extralit training \
  --name my-dataset \
  --framework transformers \
  --model bert-base-uncased \
  --workspace my-workspace \
  --train-size 0.8 \
  --seed 42 \
  --device 0 \
  --output-dir models/my-model
```

## Troubleshooting

### Authentication Issues

If you have authentication problems:
1. Verify your API key is correct
2. Check the server URL is accessible
3. Try logging out and back in

### Command Failures

If a command fails:
1. Confirm you're authenticated
2. Check you have necessary permissions
3. Verify resources exist
4. Add `--debug` flag for detailed error information

### Getting Help

For any command, add `--help` to see detailed usage information:
```bash
extralit <command> --help
```

For server information:
```bash
extralit info
```



