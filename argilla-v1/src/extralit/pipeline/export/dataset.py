from typing import Dict, List, Optional, Literal, Union, Any

import argilla as rg
import pandas as pd
import pandera as pa
from argilla import SpanLabelOption


def create_papers_dataset(
        schema: pa.DataFrameSchema,
        papers: pd.DataFrame,
        fields: List[rg.TextField] = None,
        span_columns: Optional[Dict[str, Union[Dict[str, str], List[SpanLabelOption]]]] = None,
        metadata_columns: Optional[List[str]] = None,
        vectors_settings: List[rg.VectorSettings] = None,
        **kwargs) -> rg.FeedbackDataset:
    fields = fields or []
    questions = []
    metadata_properties = {}
    assert not metadata_columns or papers.columns.intersection(metadata_columns).size == len(metadata_columns), \
        "Some column in `metadata_columns` not found in the papers dataframe"
    assert not span_columns or papers.columns.intersection(span_columns).size == len(span_columns), \
        "Some column in `span_columns` not found in the papers dataframe"

    for index_name in (schema.index.names if schema.index else []):
        metadata_properties[index_name] = rg.TermsMetadataProperty(name=index_name, title=index_name.capitalize(),
                                                                   visible_for_annotators=True)

    # Questions
    for field_name, column in schema.columns.items():
        is_multiselect = any(check.name == 'multiselect' for check in column.checks)
        if column.dtype.type == bool:
            question = rg.LabelQuestion(
                name=field_name, title=column.title or field_name, description=column.description,
                labels={'True': 'YES', 'False': 'NO'}, required=not column.nullable)

        elif column.dtype.type == list:
            labels = next((check.statistics['isin'] for check in column.checks if 'isin' in check.statistics), None)
            question = rg.MultiLabelQuestion(
                name=field_name, title=column.title or field_name, description=column.description,
                labels=labels, required=not column.nullable)

        elif is_multiselect:
            labels = next((check.statistics['isin'] for check in column.checks if check.name == 'multiselect'), None)
            question = rg.MultiLabelQuestion(
                name=field_name, title=column.title or field_name, description=column.description,
                labels=labels, required=not column.nullable)
        else:
            question = rg.TextQuestion(
                name=field_name, title=column.title or field_name, description=column.description,
                required=not column.nullable, use_markdown=True)

        questions.append(question)

    for column_name, labels in (span_columns or {}).items():
        question = rg.SpanQuestion(
            name=f'span_{column_name}', field=column_name, title=column_name.capitalize(), labels=labels, required=False)
        questions.append(question)

    # Metadatas
    metadata_columns = papers.columns.intersection(metadata_columns or [])
    for column_name, dtype in papers.dtypes.get(metadata_columns, {}).items():
        if column_name in schema.columns or column_name == "file_path": continue
        try:
            if dtype == bool:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize(), visible_for_annotators=True)
            elif dtype == float:
                metadata_prop = rg.FloatMetadataProperty(name=column_name, title=column_name.capitalize(), visible_for_annotators=True)
            elif dtype == int:
                metadata_prop = rg.IntegerMetadataProperty(name=column_name, title=column_name.capitalize(), visible_for_annotators=True)
            elif dtype == object:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize(), visible_for_annotators=True)
            else:
                metadata_prop = rg.TermsMetadataProperty(name=column_name, title=column_name.capitalize(), visible_for_annotators=True)

            metadata_properties[column_name] = metadata_prop
        except Exception as e:
            print(f"Failed to define metadata property {column_name} for the dataset: {e}")

    if not any(field.name == 'metadata' for field in fields):
        fields.insert(0, rg.TextField(name="metadata", title="Metadata", use_markdown=True))

    return rg.FeedbackDataset(
        fields=fields,
        questions=questions,
        metadata_properties=list(metadata_properties.values()) if metadata_properties else None,
        guidelines=schema.description,
        vectors_settings=vectors_settings,
        **kwargs
    )


def create_extraction_dataset(
        fields: Optional[List[rg.TextField]]=None,
        questions: Optional[List[rg.TextQuestion]]=None,
        metadata_properties: Optional[List[rg.TermsMetadataProperty]] = None,
        vectors_settings: Optional[List[rg.VectorSettings]]=None) -> rg.FeedbackDataset:
    extraction_dataset = rg.FeedbackDataset(
        guidelines="Manually validate every data entries in the data extraction sheet to build a "
                   "gold-standard validation dataset.",
        fields=[
            rg.TextField(name="metadata", title="Reference:", required=True, use_markdown=True),
            rg.TextField(name="extraction", title="Extracted data:", required=True, use_table=True),
            rg.TextField(name="context", title="Top relevant segments:", required=False, use_markdown=True),
            *(fields or [])
        ],
        questions=[
            rg.MultiLabelQuestion(
                name="context-relevant",
                title="Which of the document section(s) attributed to this data extraction table?",
                description="Please identify which section in the source PDF the data extract came from, and select the matching section header(s) in this multi-selection list.",
                type='dynamic_multi_label_selection',
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
                use_table=True,
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
        vectors_settings=vectors_settings,
        metadata_properties=[
            rg.TermsMetadataProperty(
                name="reference",
                title="Reference",
                visible_for_annotators=True),
            rg.TermsMetadataProperty(
                name="type",
                title="Question Type",
                visible_for_annotators=True),
            *(metadata_properties or [])
        ],
    )

    return extraction_dataset

def create_preprocessing_dataset():
    dataset = rg.FeedbackDataset(
        fields=[
            rg.TextField(name="metadata", title='Metadata:', required=True,
                         use_markdown=True),
            rg.TextField(name="header", title='Title:', required=True,
                         use_markdown=True),
            rg.TextField(name="image", title='Image:', required=False,
                         use_markdown=True),
            rg.TextField(name="text-1", title='Method 1:', required=False,
                         use_markdown=True, use_table=False),
            rg.TextField(name="text-2", title='Method 2:', required=False,
                         use_markdown=True, use_table=False),
            rg.TextField(name="text-3", title='Method 3:', required=False,
                         use_markdown=True, use_table=False),
            rg.TextField(name="text-4", title='Method 4:', required=False,
                         use_markdown=True, use_table=False),
            rg.TextField(name="text-5", title='Method 5:', required=False,
                         use_markdown=True, use_table=False),
        ],
        questions=[
            rg.LabelQuestion(
                name="ranking",
                title='Which method extracted the most complete and accurate information?',
                labels={'text-1': "Method 1", 'text-2': "Method 2", 'text-3': "Method 3", 'text-4': "Method 4",
                        'text-5': "Method 5", 'none': "None"},
                type='dynamic_label_selection',
                required=True),
            rg.MultiLabelQuestion(
                name="mismatched",
                title="Which of the method(s) extracted the wrong table/figure? (if any)",
                description="This indication helps in evaluating these models accuracy",
                type='dynamic_multi_label_selection',
                labels={'text-1': "Method 1", 'text-2': "Method 2", 'text-3': "Method 3", 'text-4': "Method 4",
                        'text-5': "Method 5"},
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
                use_markdown=True, use_table=True,
            ),
            rg.TextQuestion(
                name="notes",
                title="Mention any notes here",
                required=False,
                use_markdown=False,
            ),
        ],
        metadata_properties=[
            rg.TermsMetadataProperty(name="reference", title="Reference"),
            rg.TermsMetadataProperty(name="page_number", title="Page Number"),
            rg.TermsMetadataProperty(name="number", title="Table/Figure Number"),
            rg.TermsMetadataProperty(name="type", title="Element type"),
            rg.TermsMetadataProperty(name="pmid", title="Document Pubmed ID"),
            rg.TermsMetadataProperty(name="doc_id", title="Document ID", visible_for_annotators=False),
            rg.FloatMetadataProperty(name="probability", title="Detection probability"),
            rg.TermsMetadataProperty(name="annotators"),
        ],
    )

    return dataset