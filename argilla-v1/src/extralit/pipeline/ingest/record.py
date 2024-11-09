from datetime import datetime
from typing import Optional, Union, List, Dict, Any, Literal

import argilla as rg
from argilla.client.feedback.schemas.remote.records import RemoteFeedbackRecord
from argilla.client.sdk.users.models import UserModel

from extralit.convert.json_table import is_json_table
from extralit.pipeline.update.suggestion import get_record_suggestion_value

def get_record_data(
    record: Union[RemoteFeedbackRecord, rg.FeedbackRecord],
    fields: Optional[Union[List[str], str]] = None,
    answers: Optional[Union[List[str], str]] = None,
    suggestions: Optional[Union[List[str], str]] = None,
    metadatas: Optional[Union[List[str], str]] = None,
    users: Optional[Union[List[rg.User], rg.User]] = None,
    include_user_id:bool=False,
    status: Optional[List[Literal['submitted', 'draft', 'pending', 'discarded']]] = ['submitted', 'draft'],
) -> Dict[str, Any]:
    """
    Extracts data from a feedback record based on the specified parameters.

    Args:
        record (Union[RemoteFeedbackRecord, rg.FeedbackRecord]): The feedback record to extract data from.
        fields (Union[List[str], str]): The fields to extract from the record.
        answers (Optional[Union[List[str], str]]): The answers to extract from the record's responses.
        suggestions (Optional[Union[List[str], str]]): The suggestions to extract from the record's responses.
        metadatas (Optional[Union[List[str], str]]): The metadata keys to extract from the record.
        users (Optional[Union[List[rg.User], rg.User]]): The users whose responses should be considered.
        include_user_id (bool, optional): Whether to include the user ID in the output. Defaults to False.
        include_consensus (Optional[str], optional): If not None, then include the concensus status with the provided key as the argument. Defaults to None.
        status (Optional[List[str]], optional): The statuses to filter. Defaults to ["submited"].

    Returns:
        Dict[str, Any]: A dictionary containing the extracted data.

    """
    fields = [fields] if isinstance(fields, str) else set(fields) if fields else []
    answers = [answers] if isinstance(answers, str) else set(answers) if answers else []
    suggestions = [suggestions] if isinstance(suggestions, str) else set(suggestions) if suggestions else []
    metadatas = [metadatas] if isinstance(metadatas, str) else set(metadatas) if metadatas else []
    users = [users] if isinstance(users, (UserModel, rg.User)) else list(users) if users else []
    responses = record.responses

    if users:
        user_ids = {u.id for u in users}
        responses = [r for r in responses if r.user_id in user_ids]

    if status:
        responses = [r for r in responses if r.status.value in status]
    data = {}
    for field in fields:
        if field in record.fields:
            data[field] = record.fields[field]

    for suggestion in suggestions:
        data[suggestion] = get_record_suggestion_value(record, question_name=suggestion, users=users)

    selected_response = next((r for r in responses[::-1] if r.values), None)
    for answer in answers:
        if selected_response and answer in selected_response.values:
            data[answer] = selected_response.values[answer].value

            if include_user_id:
                data['user_id'] = selected_response.user_id

    for key in metadatas:
        if key in record.metadata and key not in data:
            data[key] = record.metadata[key]

    return data


def get_record_timestamp(record: Union[RemoteFeedbackRecord, rg.FeedbackRecord]) -> Optional[datetime]:
    timestamp = record.updated_at or record.inserted_at

    if len(record.responses):
        response = record.responses[-1]
        response_timestamp = response.updated_at or response.inserted_at
        if response_timestamp and response_timestamp > timestamp:
            timestamp = response_timestamp

    return timestamp
