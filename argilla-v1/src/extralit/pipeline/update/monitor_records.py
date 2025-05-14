import logging
from collections import defaultdict
from time import sleep
from typing import Dict, Optional, Any

import argilla as rg
from argilla.client.feedback.dataset.remote.dataset import RemoteFeedbackDataset
from argilla.client.feedback.schemas.remote.records import RemoteFeedbackRecord

from extralit.convert.json_table import json_to_df, df_to_json
from extralit.pipeline.ingest.record import get_record_table, get_record_timestamp


class MonitorIntegrationDataset:
    _logger = logging.getLogger("MonitorIntegrationDataset")
    _logger.setLevel(logging.INFO)

    def __init__(self, from_dataset: RemoteFeedbackDataset, to_dataset: RemoteFeedbackDataset) -> None:
        """


        Args:
            from_dataset (rg.FeedbackDataset): The dataset to monitor.
            to_dataset (rg.FeedbackDataset): The dataset to update.
        """
        self.from_dataset = from_dataset
        self.to_dataset = to_dataset
        self._records = None
        self.fetch_records()

    def fetch_records(self) -> None:
        # Caches the records in a dict with the reference as key for faster access
        self._records = {record.metadata['reference']: record for record in self.to_dataset.records}

    @property
    def records(self) -> Dict[str, RemoteFeedbackRecord]:
        return self._records

    def create_record(self, reference: str, metadata: Dict[str, Any]) -> rg.FeedbackRecord:
        if 'type' in metadata:
            del metadata['type']  # Remove the type from the metadata
        record = rg.FeedbackRecord(
            fields={
                'metadata': reference,
            },
            metadata=metadata,
        )
        return record

    def monitor(self, batch_size: int = 5, infinite: bool = True) -> None:
        """
        Monitor the dataset by processing it in batches.

        Args:
            batch_size (int): Size of each batch.
        """
        extractions_batch = defaultdict(lambda: {})
        last_batch_size = 0

        while True:
            for record in self.from_dataset:
                reference = record.metadata['reference']

                extraction = get_record_table(record, field='extraction', answer='extraction-correction')
                updated_at = get_record_timestamp(record)

                # Update timestamp if newer
                if 'updated_at' not in extractions_batch[reference] or \
                        not extractions_batch[reference]['updated_at'] or \
                        (updated_at and updated_at > extractions_batch[reference]['updated_at']):
                    extractions_batch[reference]['updated_at'] = updated_at

                # Add extraction to batch
                if extraction:
                    question_type = record.metadata['type']
                    extractions_batch[reference][question_type] = extraction
                    extractions_batch[reference]['metadata'] = record.metadata

            # Check if the batch should be processed
            if len(extractions_batch) >= batch_size or \
                    (len(extractions_batch) > 0 and len(extractions_batch) == last_batch_size):
                extractions_batch = self.process_batch(extractions_batch)
                last_batch_size = 0  # Reset the last batch size after processing
            else:
                last_batch_size = len(extractions_batch)  # Update last batch size

            if not infinite:
                break
            sleep(2)

        if extractions_batch:
            self.process_batch(extractions_batch)

    def process_batch(self, extractions_batch: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Add/Update the records to the `to_dataset` with the extractions in the batch.

        Args:
            extractions_batch (Dict[str, Dict[str, Any]]): A dict with the reference as key and a dict with the
                `from_dataset` records as value.
        """

        update_records = {}
        add_records = {}
        for reference, extractions in extractions_batch.items():
            if not extractions['updated_at']:
                continue

            is_new_record = reference not in self.records

            if is_new_record:
                record = rg.FeedbackRecord(
                    fields={
                        'metadata': f'[{reference}](dataset/{self.from_dataset.id}/annotation-mode?_page=1&_status=valid&_metadata=reference.{reference})',
                    },
                    metadata={k: v for k, v in extractions['metadata'].items() if k != 'type'},
                )
            else:
                # Check if record need to be updated
                record = self.records[reference]
                if extractions['updated_at'] and extractions['updated_at'] <= get_record_timestamp(record):
                    continue


            if is_new_record:
                add_records[reference] = record
            else:
                update_records[reference] = record

        sep = '\n\t'
        if update_records:
            self._logger.info(f"Updating {len(update_records)} records: \n"
                              f"{sep.join([rec.metadata['reference'] + ' ' + str(list(rec.fields.keys())) for rec in update_records.values()])} \n")
            for record in update_records.values():
                record.updated_at = extractions_batch[record.metadata['reference']]['updated_at']
            self.to_dataset.update_records(list(update_records.values()), show_progress=False)

        if add_records:
            self._logger.info(f"Adding {len(add_records)} records: \n"
                              f"{sep.join([rec.metadata['reference'] + ' ' + str(list(rec.fields.keys())) for rec in add_records.values()])} \n")
            self.to_dataset.add_records(list(add_records.values()), show_progress=False)
            self.fetch_records()

        # reset batch to only last reference
        new_batch = defaultdict(lambda: {})
        return new_batch
