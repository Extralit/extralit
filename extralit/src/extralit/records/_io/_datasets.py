# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import warnings
from typing import TYPE_CHECKING, Any, Optional, Union

import lazy_loader as lazy

from extralit._helpers._media import pil_to_data_uri, uncast_image
from extralit.records._io._generic import GenericIO

datasets = lazy.load("datasets")


if TYPE_CHECKING:
    from datasets import ClassLabel
    from datasets import Dataset as HFDataset

    from extralit.datasets import Dataset
    from extralit.records import Record
    from extralit.records._mapping import IngestedRecordMapper


def _cast_images_as_urls(hf_dataset: "HFDataset", columns: list[str]) -> "HFDataset":
    """Cast the image features in the Hugging Face dataset as URLs.

    Parameters:
        hf_dataset (HFDataset): The Hugging Face dataset to cast.
        columns (List[str]): The names of the columns containing the image features.

    Returns:
        HFDataset: The Hugging Face dataset with image features cast as URLs.
    """

    for column in columns:
        # make an updated features object with the new column type
        features = hf_dataset.features.copy()
        features[column] = datasets.Value("string")  # type: ignore
        # cast the column in batches
        hf_dataset = hf_dataset.map(
            function=lambda batch: {column: [pil_to_data_uri(sample) for sample in batch]},
            with_indices=False,
            batched=True,
            input_columns=[column],
            remove_columns=[column],
            features=features,
        )

    return hf_dataset


def _int2class_name(feature: "ClassLabel", value: int) -> Optional[str]:
    try:
        return feature.int2str(value)
    except Exception as ex:
        warnings.warn(f"Could not cast {value} to string. Error: {ex}", stacklevel=2)
        return None


def _cast_class_label_sequence_as_string_list(hf_dataset: "HFDataset", columns: list[str]) -> "HFDataset":
    def map2str_list(x: dict, column_name: str, features: dict):
        value = x[column_name]
        feature = features[column]

        value = [_int2class_name(feature.feature, v) for v in value]
        return {column: value}

    for column in columns:
        features = hf_dataset.features.copy()
        features[column] = datasets.Sequence(datasets.Value("string"))  # type: ignore
        hf_dataset = hf_dataset.map(
            map2str_list,
            fn_kwargs={"column_name": column, "features": hf_dataset.features},
            features=features,
        )

    return hf_dataset


def _cast_classlabels_as_strings(hf_dataset: "HFDataset", columns: list[str]) -> "HFDataset":
    """Cast the class label features in the Hugging Face dataset as strings.

    Parameters:
        hf_dataset (HFDataset): The Hugging Face dataset to cast.
        columns (List[str]): The names of the columns containing the class label features.

    Returns:
        HFDataset: The Hugging Face dataset with class label features cast as strings.
    """

    def label_column2str(x: dict, column: str, features: dict) -> dict[str, Union[str, None]]:
        value = x[column]
        feature = features[column]

        value = _int2class_name(feature, value)
        return {column: value}

    for column in columns:
        features = hf_dataset.features.copy()
        features[column] = datasets.Value("string")  # type: ignore
        hf_dataset = hf_dataset.map(
            label_column2str, fn_kwargs={"column": column, "features": hf_dataset.features}, features=features
        )

    return hf_dataset


def _uncast_uris_as_images(hf_dataset: "HFDataset", columns: list[str]) -> "HFDataset":
    """Cast the image features in the Hugging Face dataset as PIL images.

    Parameters:
        hf_dataset (HFDataset): The Hugging Face dataset to cast.
        columns (List[str]): The names of the columns containing the image features.

    Returns:
        HFDataset: The Hugging Face dataset with image features cast as PIL images.
    """

    casted_hf_dataset = hf_dataset

    for column in columns:
        features = hf_dataset.features.copy()
        features[column] = datasets.Image()  # type: ignore
        casted_hf_dataset = hf_dataset.map(
            function=lambda batch: {column: [uncast_image(sample) for sample in batch]},
            with_indices=False,
            batched=True,
            input_columns=[column],
            remove_columns=[column],
            features=features,
        )
        try:
            casted_hf_dataset[0]
        except FileNotFoundError:
            warnings.warn(
                f"Image file not found for column {column}. Image will be persisted as string (URL, path, or base64).",
                stacklevel=2,
            )
            casted_hf_dataset = hf_dataset

    return casted_hf_dataset


def _uncast_label_questions_as_classlabels(hf_dataset: "HFDataset", columns: list[str]) -> "HFDataset":
    """Cast the class label features in the Hugging Face dataset as strings.

    Parameters:
        hf_dataset (HFDataset): The Hugging Face dataset to cast.
        columns (List[str]): The names of the columns containing the class label features.

    Returns:
        HFDataset: The Hugging Face dataset with class label features cast as strings.
    """
    for column in columns:
        column = f"{column}.suggestion"
        if column not in hf_dataset.column_names:
            continue
        values = list(hf_dataset.unique(column))
        features = hf_dataset.features.copy()
        features[column] = datasets.ClassLabel(names=values)  # type: ignore
        hf_dataset = hf_dataset.map(
            function=lambda batch: {column: [values.index(sample) for sample in batch]},
            with_indices=False,
            batched=True,
            input_columns=[column],
            remove_columns=[column],
            features=features,
        )
    return hf_dataset


ATTRIBUTE_UNCASTERS = {
    "image": _uncast_uris_as_images,
    "label_selection": _uncast_label_questions_as_classlabels,
}


class HFDatasetsIO:
    @staticmethod
    def _is_hf_dataset(dataset: Any) -> bool:
        """Check if the object is a Hugging Face dataset.

        Parameters:
            dataset (Dataset): The object to check.

        Returns:
            bool: True if the object is a Hugging Face dataset, False otherwise.
        """
        return isinstance(dataset, datasets.Dataset)  # type: ignore

    @staticmethod
    def to_datasets(records: list[Union["Record", tuple["Record", float]]], dataset: "Dataset") -> "HFDataset":
        """
        Export the records to a Hugging Face dataset.

        Returns:
            The dataset containing the records.
        """
        record_dicts = GenericIO.to_dict(records, flatten=True)
        hf_dataset = datasets.Dataset.from_dict(record_dicts)  # type: ignore
        hf_dataset = HFDatasetsIO._uncast_argilla_attributes_to_datasets(hf_dataset, dataset.schema)
        return hf_dataset

    @staticmethod
    def _record_dicts_from_datasets(
        hf_dataset: "HFDataset", mapper: "IngestedRecordMapper"
    ) -> list[dict[str, Union[str, float, int, list]]]:
        """Creates a dictionaries from an HF dataset that can be passed to DatasetRecords.add or DatasetRecords.update.

        Parameters:
            hf_dataset (HFDataset): The dataset containing the records.

        Returns:
            Generator[Dict[str, Union[str, float, int, list]], None, None]: A generator of dictionaries to be passed to DatasetRecords.add or DatasetRecords.update.
        """

        hf_dataset = HFDatasetsIO.to_argilla(hf_dataset=hf_dataset, mapper=mapper)

        try:
            hf_dataset = hf_dataset.to_iterable_dataset()
        except AttributeError:
            pass

        record_dicts = list(hf_dataset)
        return record_dicts

    @staticmethod
    def _uncast_argilla_attributes_to_datasets(hf_dataset: "HFDataset", schema: dict) -> "HFDataset":
        """Get the names of the Extralit fields that contain image data.

        Parameters:
            hf_dataset (Dataset): The dataset to check.

        Returns:
            HFDataset: The dataset with argilla attributes uncasted.
        """

        for attribute_type, uncaster in ATTRIBUTE_UNCASTERS.items():
            attributes = []
            for attribute_name, attribute_schema in schema.items():
                if hasattr(attribute_schema, "type") and attribute_schema.type == attribute_type:
                    attributes.append(attribute_name)
            if attributes:
                hf_dataset = uncaster(hf_dataset, attributes)
        return hf_dataset

    @staticmethod
    def to_argilla(hf_dataset: "HFDataset", mapper: "IngestedRecordMapper") -> "HFDataset":
        """Check if the Hugging Face dataset contains image features.

        Parameters:
            hf_dataset (HFDataset): The Hugging Face dataset to check.

        Returns:
            bool: True if the Hugging Face dataset contains image features, False otherwise.
        """
        id_column_name = mapper.mapping.id.source
        if id_column_name not in hf_dataset.column_names:
            split = hf_dataset.split
            warnings.warn(
                stacklevel=2,
                message="Record id column not found in Hugging Face dataset. Using row index and split for record ids.",
            )

            hf_dataset = hf_dataset.map(
                lambda row, idx: {id_column_name: f"{split}_{idx}"},
                with_indices=True,
            )

        image_columns = []
        class_label_columns = []
        class_label_sequence_columns = []

        for name, feature in hf_dataset.features.items():
            if isinstance(feature, datasets.Image):  # type: ignore
                image_columns.append(name)
            elif isinstance(feature, datasets.ClassLabel):  # type: ignore
                class_label_columns.append(name)
            elif isinstance(feature, datasets.Sequence) and isinstance(feature.feature, datasets.ClassLabel):  # type: ignore
                class_label_sequence_columns.append(name)

        if image_columns:
            hf_dataset = _cast_images_as_urls(hf_dataset, image_columns)

        if class_label_columns:
            hf_dataset = _cast_classlabels_as_strings(hf_dataset, class_label_columns)

        if class_label_sequence_columns:
            hf_dataset = _cast_class_label_sequence_as_string_list(hf_dataset, class_label_sequence_columns)

        return hf_dataset
