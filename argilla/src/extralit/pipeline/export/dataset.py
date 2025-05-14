from typing import Dict, List, Optional, Literal, Union, Any

import argilla as rg
import pandas as pd
import pandera as pa


def create_papers_dataset(
        schema: pa.DataFrameSchema,
        papers: pd.DataFrame,
        name: str,
        workspace: str,
        fields: List[rg.TextField] = None,
        span_columns: Optional[Dict[str, Union[Dict[str, str], List[str]]]] = None,
        metadata_columns: Optional[List[str]] = None,
        vectors: List[rg.VectorField] = None,
        **kwargs) -> rg.Dataset:
    fields = fields or []
    questions = []
    metadata_properties = {}
    assert not metadata_columns or papers.columns.intersection(metadata_columns).size == len(metadata_columns), \
        "Some column in `metadata_columns` not found in the papers dataframe"
    assert not span_columns or papers.columns.intersection(span_columns).size == len(span_columns), \
        "Some column in `span_columns` not found in the papers dataframe"

    for index_name in (schema.index.names if schema.index else []):
        metadata_properties[index_name] = rg.TermsMetadataProperty(
            name=index_name,
            title=index_name.capitalize()
        )

    # Questions
    for field_name, column in schema.columns.items():
        is_multiselect = any(check.name == 'multiselect' for check in column.checks)
        if column.dtype.type == bool:
            question = rg.LabelQuestion(
                name=field_name,
                labels={'True': 'YES', 'False': 'NO'},
                title=column.title or field_name,
                description=column.description,
                required=not column.nullable
            )
        elif column.dtype.type == list:
            labels = next((check.statistics['isin'] for check in column.checks if 'isin' in check.statistics), None)
            question = rg.MultiLabelQuestion(
                name=field_name,
                labels=labels,
                title=column.title or field_name,
                description=column.description,
                required=not column.nullable
            )
        elif is_multiselect:
            labels = next((check.statistics['isin'] for check in column.checks if check.name == 'multiselect'), None)
            question = rg.MultiLabelQuestion(
                name=field_name,
                labels=labels,
                title=column.title or field_name,
                description=column.description,
                required=not column.nullable
            )
        else:
            question = rg.TextQuestion(
                name=field_name,
                title=column.title or field_name,
                description=column.description,
                required=not column.nullable,
                use_markdown=True
            )
        questions.append(question)

    for column_name, labels in (span_columns or {}).items():
        question = rg.SpanQuestion(
            name=f'span_{column_name}',
            labels=labels,
            field=column_name,
            title=column_name.capitalize(),
            required=False
        )
        questions.append(question)

    # Metadata
    metadata_columns = papers.columns.intersection(metadata_columns or [])
    for column_name, dtype in papers.dtypes.get(metadata_columns, {}).items():
        if column_name in schema.columns or column_name == "file_path":
            continue
        try:
            if dtype == bool:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize())
            elif dtype == float:
                metadata_prop = rg.FloatMetadataProperty(name=column_name, title=column_name.capitalize())
            elif dtype == int:
                metadata_prop = rg.IntegerMetadataProperty(name=column_name, title=column_name.capitalize())
            elif dtype == object:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize())
            else:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize())

            metadata_properties[column_name] = metadata_prop
        except Exception as e:
            print(f"Failed to define metadata property {column_name} for the dataset: {e}")

    if not any(field.name == 'metadata' for field in fields):
        fields.insert(0, rg.TextField(name="metadata", title="Metadata", use_markdown=True))

    settings = rg.Settings(
        fields=fields,
        questions=questions,
        metadata=list(metadata_properties.values()) if metadata_properties else None,
        guidelines=schema.description,
        vectors=vectors,
        **kwargs
    )

    return rg.Dataset(name=name, workspace=workspace, settings=settings)


def create_extraction_dataset(
        name: str,
        workspace: str,
        fields: Optional[List[rg.TextField]] = None,
        questions: Optional[List[rg.TextQuestion]] = None,
        metadata_properties: Optional[List[rg.TermsMetadataProperty]] = None,
        vectors: Optional[List[rg.VectorField]] = None) -> rg.Dataset:

    settings = rg.Settings(
        guidelines="Manually validate every data entries in the data extraction sheet to build a "
                  "gold-standard validation dataset.",
        fields=[
            rg.TextField(name="metadata", title="Reference:", required=True, use_markdown=True),
            rg.TextField(name="extraction", title="Extracted data:", required=True),
            rg.TextField(name="context", title="Top relevant segments:", required=False, use_markdown=True),
            *(fields or [])
        ],
        questions=[
            rg.MultiLabelQuestion(
                name="context-relevant",
                title="Which of the document section(s) attributed to this data extraction table?",
                description="Please identify which section in the source PDF the data extract came from, and select the matching section header(s) in this multi-selection list.",
                labels=['Not listed'],
                visible_labels=3,
                required=False,
            ),
            rg.MultiLabelQuestion(
                name="extraction-source",
                title="Where did the extracted data primarily came from?",
                labels=["Text", "Table", "Figure"],
                required=False,
            ),
            rg.TextQuestion(
                name="extraction-correction",
                title="Provide a correction to the extracted data:",
                required=True,
            ),
            rg.TextQuestion(
                name="notes",
                title="Mention any notes for other extractors (or prompt for the LLM)",
                required=False,
                use_markdown=True,
            ),
            rg.TextQuestion(
                name="issue",
                title="Flag an issue for discrepancy between the Suggestion's extraction and your own extraction for Consensus Review",
                description="If you are an extractor, please do not choose Approve, but you may choose Needs Review to flag an issue to discuss in a Consensus review. "
                          "If you are a reviewer, choose Approve to validate the extraction, or Needs redo extraction to let extractors know this record needs further work.",
                required=False,
                use_markdown=True,
            ),
            *(questions or [])
        ],
        vectors=vectors,
        metadata=[
            rg.TermsMetadataProperty(
                name="reference",
                title="Reference"),
            rg.TermsMetadataProperty(
                name="type",
                title="Question Type"),
            *(metadata_properties or [])
        ],
    )

    return rg.Dataset(name=name, workspace=workspace, settings=settings)


def create_preprocessing_dataset(name: str, workspace: str) -> rg.Dataset:
    settings = rg.Settings(
        fields=[
            rg.TextField(name="metadata", title='Metadata:', required=True,
                      use_markdown=True),
            rg.TextField(name="header", title='Title:', required=True,
                      use_markdown=True),
            rg.TextField(name="image", title='Image:', required=False,
                      use_markdown=True),
            rg.TextField(name="text-1", title='Method 1:', required=False,
                      use_markdown=True),
            rg.TextField(name="text-2", title='Method 2:', required=False,
                      use_markdown=True),
            rg.TextField(name="text-3", title='Method 3:', required=False,
                      use_markdown=True),
            rg.TextField(name="text-4", title='Method 4:', required=False,
                      use_markdown=True),
            rg.TextField(name="text-5", title='Method 5:', required=False,
                      use_markdown=True),
        ],
        questions=[
            rg.LabelQuestion(
                name="ranking",
                title='Which method extracted the most complete and accurate information?',
                labels={'text-1': "Method 1", 'text-2': "Method 2", 'text-3': "Method 3",
                       'text-4': "Method 4", 'text-5': "Method 5", 'none': "None"},
                required=True),
            rg.MultiLabelQuestion(
                name="mismatched",
                title="Which of the method(s) extracted the wrong table/figure? (if any)",
                description="This indication helps in evaluating these models accuracy",
                labels={'text-1': "Method 1", 'text-2': "Method 2", 'text-3': "Method 3",
                       'text-4': "Method 4", 'text-5': "Method 5"},
                required=False,
            ),
            rg.TextQuestion(
                name="header-correction",
                title="Correct the table or figure title:",
                required=False,
                use_markdown=False,
            ),
            rg.TextQuestion(
                name="text-correction",
                title="Correct the extracted data:",
                required=False,
                use_markdown=True,
            ),
            rg.TextQuestion(
                name="notes",
                title="Mention any notes here",
                required=False,
                use_markdown=False,
            ),
        ],
        metadata=[
            rg.TermsMetadataProperty(name="reference", title="Reference"),
            rg.TermsMetadataProperty(name="page_number", title="Page Number"),
            rg.TermsMetadataProperty(name="number", title="Table/Figure Number"),
            rg.TermsMetadataProperty(name="type", title="Element type"),
            rg.TermsMetadataProperty(name="pmid", title="Document Pubmed ID"),
            rg.TermsMetadataProperty(name="doc_id", title="Document ID"),
            rg.FloatMetadataProperty(name="probability", title="Detection probability"),
            rg.TermsMetadataProperty(name="annotators"),
        ],
    )

    return rg.Dataset(name=name, workspace=workspace, settings=settings)
