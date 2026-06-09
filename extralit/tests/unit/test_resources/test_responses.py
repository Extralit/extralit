import uuid

import pytest

from extralit import Dataset, Record, Response, UserResponse, Workspace
from extralit._models import ResponseStatus, UserResponseModel


class TestResponses:
    def test_create_user_response(self):
        user_id = uuid.uuid4()
        response = UserResponse(
            responses=[
                Response(question_name="question", value="answer", user_id=user_id),
                Response(question_name="other-question", value="answer", user_id=user_id),
            ],
        )

        assert response.to_dict() == {
            "values": {
                "question": {"value": "answer"},
                "other-question": {"value": "answer"},
            },
            "status": "draft",
            "user_id": str(user_id),
        }

    def test_create_submitted_user_responses(self):
        user_id = uuid.uuid4()
        response = UserResponse(
            responses=[
                Response(question_name="question", value="answer", user_id=user_id, status="submitted"),
                Response(question_name="other-question", value="answer", user_id=user_id, status="submitted"),
            ],
        )

        assert response.to_dict() == {
            "values": {
                "question": {"value": "answer"},
                "other-question": {"value": "answer"},
            },
            "status": "submitted",
            "user_id": str(user_id),
        }

    def test_create_user_response_with_multiple_status(self):
        user_id = uuid.uuid4()
        response = UserResponse(
            responses=[
                Response(question_name="question", value="answer", user_id=user_id, status="draft"),
                Response(question_name="other-question", value="answer", user_id=user_id, status="submitted"),
            ],
        )

        assert response.to_dict() == {
            "values": {
                "question": {"value": "answer"},
                "other-question": {"value": "answer"},
            },
            "status": "draft",
            "user_id": str(user_id),
        }

    def test_create_user_response_with_multiple_user_id(self):
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Multiple user_ids found in user responses"):
            UserResponse(
                responses=[
                    Response(question_name="question", value="answer", user_id=user_id),
                    Response(question_name="other-question", value="answer", user_id=other_user_id),
                ],
            )

    def test_create_user_response_from_draft_response_model_without_values(self):
        model = UserResponseModel(values={}, status=ResponseStatus.draft, user=uuid.uuid4())

        record = Record(
            fields={"question": "answer"},
            _dataset=Dataset(name="burr", workspace=Workspace(name="test", id=uuid.uuid4())),
        )

        response = UserResponse.from_model(model=model, record=record)

        assert len(response.responses) == 0
        assert response.user_id is None
        assert response.status == ResponseStatus.draft
