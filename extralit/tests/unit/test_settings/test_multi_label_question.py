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
