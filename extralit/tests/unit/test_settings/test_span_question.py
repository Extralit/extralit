import extralit as ex


class TestSpanQuestions:
    def test_create_question(self):
        question = ex.SpanQuestion(
            name="span_question", field="field", allow_overlapping=True, labels=["label1", "label2", "label3"]
        )
        assert question.name == "span_question"
        assert question.field == "field"
        assert question.allow_overlapping is True
        assert question.labels == ["label1", "label2", "label3"]
        assert question.visible_labels == 3

    def test_change_field_value(self):
        question = ex.SpanQuestion(
            name="span_question", field="field", allow_overlapping=True, labels=["label1", "label2"]
        )
        question.field = "new_field"
        assert question.field == "new_field"

    def test_change_allow_overlapping_value(self):
        question = ex.SpanQuestion(
            name="span_question", field="field", allow_overlapping=True, labels=["label1", "label2"]
        )
        question.allow_overlapping = False
        assert question.allow_overlapping is False

    def test_change_labels_value(self):
        question = ex.SpanQuestion(
            name="span_question", field="field", allow_overlapping=True, labels=["label1", "label2", "label3"]
        )
        question.labels = ["label1", "label2"]
        assert question.labels == ["label1", "label2"]
        assert question.visible_labels == 3
