from typing import Dict, List

import argilla as rg
import pandera as pa


def pandera_schema_to_argilla_dataset(
        schema: pa.DataFrameSchema,
        fields: Dict[str, str],
        vectors_settings: List[rg.VectorSettings] = None,
        **kwargs) -> rg.FeedbackDataset:
    questions = []
    metadata_properties = []

    for field, column in schema.columns.items():
        if field == "reference":
            metadata_properties.append(
                rg.TermsMetadataProperty(name=field, title=field.capitalize(), visible_for_annotators=True))
            continue

        if column.dtype.type == bool:
            question = rg.LabelQuestion(
                name=field.lower(), title=column.title or field, description=column.description,
                labels={'True': 'YES', 'False': 'NO'}, required=not column.nullable)
        elif column.dtype.type == list:
            labels = next((check.statistics['isin'] for check in column.checks if 'isin' in check.statistics), None)
            question = rg.MultiLabelQuestion(
                name=field.lower(), title=column.title or field, description=column.description,
                labels=labels, required=not column.nullable)
        else:
            question = rg.TextQuestion(
                name=field.lower(), title=column.title or field, description=column.description,
                required=not column.nullable, use_markdown=True)

        questions.append(question)

    metadata_properties.extend([
        rg.TermsMetadataProperty(name="reference", title="Reference", visible_for_annotators=True),
        rg.TermsMetadataProperty(name="pmid", title="Document Pubmed ID", visible_for_annotators=True),
        rg.TermsMetadataProperty(name="doc_id", title="Document ID", visible_for_annotators=False),
        rg.TermsMetadataProperty(name="annotators", title="Annotators", visible_for_annotators=True),
    ])

    return rg.FeedbackDataset(
        fields=fields,
        questions=questions,
        metadata_properties=metadata_properties,
        guidelines=schema.description,
        vectors_settings=vectors_settings,
        **kwargs
    )
