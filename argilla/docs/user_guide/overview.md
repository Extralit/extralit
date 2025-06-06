---
description: Overview of Extralit extraction features and capabilities
---

# Project Setup

This guide shows how to create and manage extraction projects in Extralit.

## Create a New Extraction Project

First create a new extraction project by creating a Workspace. This will also create a new file storage bucket to contain schemas and PDFs. Only users added to the workspace can access the project data files and records.

```bash
extralit workspaces create {WORKSPACE_NAME}
```

## Add Team Members

Add other team-members to the project workspace as users with the `annotator` role:

```bash
extralit workspaces --name {WORKSPACE_NAME} add-user {EXISTING_USERNAME}
```

## Add New References and PDFs

Add new references to the workspace by uploading the PDF files listed in the reference table. The reference table should contain the metadata of the papers, such as the title, authors, and publication date. More specifically, the `REFERENCES_TABLE` needs to be a CSV file with the following columns:

- `reference` (str, required): The reference ID of the paper, e.g `{firstauthor_lastname}{year}{title_first_word}`.
- `pmid` (integer, nullable): The PubMed ID of the paper.
- `doi` (str, nullable): The DOI of the paper.
- `id` (str, optional): The unique UUID of the reference, for tracking with an external reference manager.
- `file_path` (str, required): The file path to the PDF file.
- `title` (str, optional): The title of the paper.
- `authors` (str, optional): The authors.
- `year` (integer, optional): The publication year of the publication.
- ...: any other reference metadata fields can be added to the table.

With the `REFERENCES_TABLE` file path in the `manifest` argument, import the references to the workspace with the `extralit references import` command, where the `metadatas` argument would add these attributes as metadatas the record.

```bash
extralit documents import --workspace {WORKSPACE_NAME} --papers {path/to/REFERENCES_TABLE.csv} --metadatas title,authors,year
```



# Extraction Processes

## Create/Update Data Extraction Schemas

The data extraction schemas are defined in Python files in the `schemas/` directory. The schemas define the structure and relationships of the data fields to be extracted from each reference. There is an AI assistant tool to help with create new schemas or update existing schemas.

Upload these schemas the extralit server with:

```bash
extralit schemas upload --workspace {WORKSPACE_NAME} --schemas {path/to/schemas/*.json}
```
Use [8 - JT - LLM Extraction.ipynb](#) if the command line tool hasn't been implemented.

## Run the PDF Preprocessing Step

The PDF preprocessing step is a computationally intensive step that uses AI OCR algorithms to detect and correct table structures within documents. The PDF preprocessing step is run on the PDF files in the workspace, and the text OCR outputs are stored in the `preprocessing/` directory and the table outputs are automatically pushed as records to the `PDF-Preprocessing` Argilla dataset for manual correction.

```bash
pip install --upgrade "extralit-server[ocr,pdf]"
extralit preprocessing run --workspace {WORKSPACE_NAME} --references {REFERENCE_IDS} --text-ocr {TABLE_OCR_MODELS} --table-ocr {TABLE_OCR_MODELS} --output-dataset {DATASET_NAME}
```
Use [5 - JT - PDF Preprocessing.ipynb](#) if the command line tool hasn't been implemented.

## Run the Initial LLM Extraction Step

After the manual corrections are made to the PDF preprocessing outputs, the LLM extraction step is run to extract the data fields defined in the schemas. The records are automatically pushed to the `2-Data-Extraction` Argilla dataset for manual correction.

```bash
pip install --upgrade "extralit-server[llm]"
extralit extraction run --workspace {WORKSPACE_NAME} --references {REFERENCE_IDS} --output-dataset {DATASET_NAME}
```
Use [8 - JT - LLM Extraction.ipynb](#) if the command line tool hasn't been implemented.

## Getting the Status of the Extractions

Check the status of the extraction jobs with the `extralit extraction status` command. The status of the extraction jobs for each reference at different steps can be `pending`, `submitted`, `discarded`.

```bash
extralit extraction status --workspace {WORKSPACE_NAME} --references {REFERENCE_IDS}
```
Use [9 - JT - Concensus extractions.ipynb](#) if the command line tool hasn't been implemented.

## Export the Extracted Data

Export the extracted data from the workspace to a CSV file with the `extralit export` command.

```bash
extralit extraction export --workspace {WORKSPACE_NAME} --output {path/to/output.csv}
```
