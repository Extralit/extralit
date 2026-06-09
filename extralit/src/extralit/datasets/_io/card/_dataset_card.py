from pathlib import Path

from huggingface_hub import DatasetCard

TEMPLATE_EXTRALIT_DATASET_CARD_PATH = Path(__file__).parent / "argilla_template.md"


class ExtralitDatasetCard(DatasetCard):
    """`ExtralitDatasetCard` has been created similarly to `DatasetCard` from
    `huggingface_hub` but with a different template. The template is located at
    `argilla/client/feedback/integrations/huggingface/card/argilla_template.md`.
    """

    default_template_path = TEMPLATE_EXTRALIT_DATASET_CARD_PATH
