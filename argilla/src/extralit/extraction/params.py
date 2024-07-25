from llama_index.core import PromptTemplate
from llama_index.core.prompts import default_prompts
from pydantic import BaseModel


class RAGExtractionParams:
    def __init__(self, output_cls=BaseModel, similarity_top_k=20, filters=None, response_mode="compact",
                 text_qa_template=PromptTemplate(default_prompts.DEFAULT_TEXT_QA_PROMPT_TMPL), **kwargs):
        self.output_cls = output_cls
        self.similarity_top_k = similarity_top_k
        self.filters = filters
        self.response_mode = response_mode
        self.text_qa_template = text_qa_template
        self.kwargs = kwargs

    def set_output_cls(self, output_cls):
        self.output_cls = output_cls

    def get_output_cls(self):
        return self.output_cls

    def set_similarity_top_k(self, similarity_top_k):
        self.similarity_top_k = similarity_top_k

    def get_similarity_top_k(self):
        return self.similarity_top_k

    def set_filters(self, filters):
        self.filters = filters

    def get_filters(self):
        return self.filters

    def set_response_mode(self, response_mode):
        self.response_mode = response_mode

    def get_response_mode(self):
        return self.response_mode

    def set_text_qa_template(self, text_qa_template):
        self.text_qa_template = text_qa_template

    def get_text_qa_template(self):
        return self.text_qa_template

    def set_kwargs(self, **kwargs):
        self.kwargs = kwargs

    def get_kwargs(self):
        return self.kwargs
