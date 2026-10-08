import extralit as ex


class TestMultiLabelQuestions:
    def test_create_question(self):
        question = ex.MultiLabelQuestion(name="span_question", labels=["label1", "label2", "label3"])
        assert question.name == "span_question"
        assert question.labels == ["label1", "label2", "label3"]
        assert question.visible_labels == 3

    def test_change_labels_value(self):
        question = ex.MultiLabelQuestion(name="span_question", labels=["label1", "label2", "label3"])
        question.labels = ["label1", "label2"]
        assert question.labels == ["label1", "label2"]
        assert question.visible_labels == 3

    def test_update_visible_labels(self):
        question = ex.MultiLabelQuestion(name="span_question", labels=["label1", "label2", "label3", "label4"])
        assert question.visible_labels == 4
        question.visible_labels = 3
        assert question.visible_labels == 3

    def test_strict_default_true(self):
        question = ex.MultiLabelQuestion(name="test_question", labels=["label1", "label2"])
        assert question.strict is True

    def test_strict_false(self):
        question = ex.MultiLabelQuestion(name="test_question", labels=["label1", "label2"], strict=False)
        assert question.strict is False

    def test_strict_setter(self):
        question = ex.MultiLabelQuestion(name="test_question", labels=["label1", "label2"])
        assert question.strict is True
        question.strict = False
        assert question.strict is False
