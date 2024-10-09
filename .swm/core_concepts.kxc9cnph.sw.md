---
description: >-
  These are the core concepts of the Extralit. They provide an overview of the
  main components and how they interact with each other.
title: core_concepts
---
# Data Extraction Workflow

The data extraction workflow in Extralit is designed to efficiently transform unstructured scientific papers into structured, analyzable data. This process involves several key steps:

1. **Document Import**: Scientific papers are imported into Extralit, typically in PDF format.

2. **Text and Table OCR**: Extralit applies several advanced OCR models to extract text and table content from the imported documents.

3. **Schema Application**: Predefined schemas are applied to guide the extraction process, specifying what data should be extracted and how it should be structured.

4. **LLM-Assisted Extraction**: Large Language Models (LLMs) are employed to assist in identifying and extracting relevant information based on the applied schemas.

5. **Manual Review and Correction**: Extracted data can be manually reviewed and corrected by researchers to ensure accuracy.

6. **Consensus Review**: For collaborative projects, multiple reviewers can assess the extracted data, and a consensus can be reached on the final dataset.

7. **Data Validation**: Extracted data is validated against the defined schemas to ensure consistency and completeness.

8. **Export**: The final structured dataset can be exported for further analysis or downstream data processes.

This workflow combines automated processes with human oversight, ensuring both efficiency and accuracy in the data extraction process. The use of LLMs and predefined schemas allows for handling complex and diverse scientific literature while maintaining consistency across large-scale extraction projects.

# Schemas and References

## Schemas

In Extralit, schemas play a crucial role in defining the structure of the organization and format of data to be extracted from scientific papers. They are defined using [Pandera](https://pandera.readthedocs.io/en/stable/) dataframe schemas, which provide flexible way to specify and validate the expected structure and content of extracted data.

Key aspects of schemas in Extralit:

1. **Column Definitions**: Schemas specify the columns that should be present in the extracted data table. Each column is defined with its name, data type, and any constraints (e.g., allowed values, numerical ranges).

2. **Data Validation**: Pandera schemas allow for complex validation rules, ensuring that extracted data meets specific criteria or relationships between fields.

3. **Nested Structures**: Schemas can represent complex, nested data structures often found in scientific literature.

4. **Relationships**: Schemas can reference one another, allowing for the representation of relationships between different tables or datasets extracted from the same paper.

Example of a simple schema definition:

```python
import pandera as pa

class StudySchema(pa.SchemaModel):
    study_id: pa.typing.Series[int] = pa.Field(gt=0)
    title: pa.typing.Series[str] = pa.Field(str_length={'min_length': 1})
    publication_year: pa.typing.Series[int] = pa.Field(ge=1900, le=2100)
    sample_size: pa.typing.Series[int] = pa.Field(gt=0)
```

## References

In Extralit, "references" refer to unique identifiers for each scientific paper in the system. These references serve several important purposes:

1. **Unique Identification**: Each paper has a unique reference, allowing for easy tracking and management of individual documents within the system.

2. **Linking Extracted Data**: All data extracted from a paper is associated with its reference, maintaining a clear connection between the source document and the extracted information.

3. **Version Control**: References can include version information, allowing for tracking of different versions or revisions of the same paper.

4. **Cross-Referencing**: When schemas define relationships between tables, references ensure that data from different tables can be correctly associated with the same source document.

By combining robust schema definitions with a clear referencing system, Extralit ensures that extracted data is well-structured, validated, and traceable back to its source, facilitating high-quality scientific data extraction and analysis.

# Workspaces and Datasets

Extralit organizes data extraction projects using workspaces and datasets, providing a scalable way to manage sequential steps in the extraction process and collaborate with team members.

## Workspaces

Workspaces in Extralit serve as the high-level container for organizing an extraction project. They provide an environment to work on verious steps of the extraction process and a reference point to consolidate the data artifacts and extraction outputs.

Key features of workspaces:

1. **Project Organization**: Group resources and tasks within a single workspace.
2. **Access Control**: Manage user permissions at the workspace level, controlling who can view, edit, or administer the workspace and its contents.
3. **Collaborative Environment**: Allow multiple team members to work on the same set of documents and extracted data.
4. **Resource Sharing**: Share common resources like schemas, documents, model ouputs, LLM configurations, and validation rules across datasets within the workspace.

## Datasets

Datasets are collections of documents and their associated extracted data within a workspace. They represent a specific extraction task or a subset of documents that are being processed together.

Key aspects of datasets:

1. **Document Collection**: A dataset contains a set of scientific papers (references) that are being processed for data extraction.
2. **Schema Association**: Each dataset is associated with one or more schemas that define the structure of the data to be extracted.
3. **Extraction Progress Tracking**: Datasets allow for tracking the progress of extraction tasks across multiple documents.
4. **Version Control**: Maintain different versions of extracted data as the extraction process progresses or as papers are updated.
5. **Export and Import**: Facilitate the export of extracted data for analysis and the import of new documents for processing.

## Workflow Integration

The workspace and dataset structure in Extralit supports a flexible workflow:

1. Create a workspace for a project to produce a desired a dataset.
2. Set up datasets within the workspace for different aspects of the project or batches of papers.
3. Import documents into the appropriate datasets.
4. Run OCR models to extract text and table content from the documents.
5. Apply schemas to guide the data extraction process.
6. Make use of LLM-assisted extraction to automate data extraction.
7. Collaborate on extraction tasks within each dataset.
8. Review and validate extracted data at the dataset level.
9. Export finalized data for analysis or integration with other research tools.

This organization allows researchers to flexibly manage large-scale literature reviews and data extraction projects, ensuring that work is well-organized, collaborative, and traceable.

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
