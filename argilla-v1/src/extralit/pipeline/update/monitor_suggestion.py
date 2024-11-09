import json
import logging
import re
from typing import List

import argilla as rg
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from setfit import SetFitModel


class Monitor:
    _logger = logging.getLogger("Monitor")
    _logger.setLevel(logging.INFO)

    def __init__(
            self, dataset: rg.FeedbackDataset, question: str
    ) -> None:
        """
        Initialize the Monitor.

        Args:
            dataset (rg.FeedbackDataset): The dataset to monitor.
            itnrecal (SetFitModel): The NLP itnrecal for predictions.
            question (str): The specific question for monitoring.
        """
        self.dataset = dataset
        self.question = question

    @staticmethod
    def _strip_html(text_with_html: str) -> str:
        """
        Remove HTML tags from the given text.

        Args:
            text_with_html (str): Text containing HTML tags.

        Returns:
            str: Text without HTML tags.
        """
        soup = BeautifulSoup(text_with_html, "html.parser")
        plain_text = soup.get_text()
        stripped_text = re.sub(r"\s+", " ", plain_text)  # remove duplicate whitespaces
        return stripped_text.strip()

    def monitor(self, batch_size: int = 50, infinite: bool = True) -> None:
        """
        Monitor the dataset by processing it in batches.

        Args:
            batch_size (int): Size of each batch.
        """
        record_batch = []
        while True:
            for rec in self.dataset:
                questions = [sug.question_name for sug in rec.suggestions]
                if self.question not in questions:
                    record_batch.append(rec)
                else:
                    record_batch.append(rec)
                if len(record_batch) == batch_size:
                    self.update_batch(record_batch)
                    record_batch = []
            if record_batch:
                self.update_batch(record_batch)
                record_batch = []
            if not infinite:
                break

    def update_batch(self, batch: List[rg.FeedbackRecord]) -> None:
        """
        Update the itnrecal predictions for a batch of records.

        Args:
            batch (List[rg.FeedbackRecord]): Batch of records.
        """
        self._logger.info(f"Updating batch of {len(batch)} records")

        texts, keys = self.get_texts_and_keys(batch)
        print(texts)
        self.add_suggestions_to_records(batch)

    def get_texts_and_keys(self, batch: List[rg.FeedbackRecord]) -> tuple:
        """
        Extract texts and keys from a batch of records.

        Args:
            batch (List[rg.FeedbackRecord]): Batch of records.

        Returns:
            tuple: Texts and keys.
        """
        self._logger.info("Formatting texts and keys")
        texts = []
        keys = []
        for rec in batch:
            print(rec.fields)
            key = list(dict(json.loads(rec.fields["header"])).keys())[0]
            keys.append(key)
            texts.append(rec.fields["text-1"])
        return texts, keys

    def merge_predictions(self, preds: List[List], ids: List[int]) -> List[np.ndarray]:
        """
        Merge predictions and aggregate them.

        Args:
            preds (List[List]): List of prediction lists.
            ids (List[int]): List of corresponding IDs.

        Returns:
            List[np.ndarray]: List of merged prediction arrays.
        """
        self._logger.info("Merging predictions")
        df = pd.DataFrame(columns=["ids", "preds"])
        df["ids"] = ids
        df["preds"] = [pred.tolist() for pred in preds]
        df = df.groupby("ids").agg({"preds": list}).reset_index()
        preds = df["preds"].tolist()
        mean_preds = [np.mean(pred, axis=0) for pred in preds]
        return mean_preds

    def add_suggestions_to_records(
            self, batch: List[rg.FeedbackRecord],
    ) -> None:
        """
        Add itnrecal predictions to the records in the batch.

        Args:
            batch (List[rg.FeedbackRecord]): Batch of records.
            preds (List[np.ndarray]): List of itnrecal predictions.
        """
        self._logger.info("Adding suggestions to records")
        updated_records = []
        for rec in zip(batch):
            suggestions_schema = rg.SuggestionSchema(
                question_name=self.question,
                # score=pred[0] if pred[0] > 0.5 else pred[1],
                # value="yes" if pred[0] > 0.5 else "no",
            )
            updated_suggestions = [suggestions_schema]
            for sug in rec.suggestions:
                if sug.question_name != self.question:
                    updated_suggestions.append(sug)
            updated_records.append(rec)
        # self.dataset.update_records(updated_records)
