import pytest

import extralit as ex
from extralit._exceptions._settings import SettingsError
from extralit.settings._io._hub import _define_settings_from_features


def test_define_settings_from_features_text():
    features = {"text_column": {"_type": "Value", "dtype": "string"}}
    settings = _define_settings_from_features(features, feature_mapping={})

    assert len(settings.fields) == 1
    assert isinstance(settings.fields[0], ex.TextField)
    assert settings.fields[0].name == "text_column"
    assert len(settings.questions) == 0


def test_define_settings_from_features_image():
    features = {"image_column": {"_type": "Image"}}
    settings = _define_settings_from_features(features, feature_mapping={})

    assert len(settings.fields) == 1
    assert isinstance(settings.fields[0], ex.ImageField)
    assert settings.fields[0].name == "image_column"


def test_define_settings_from_bool_features():
    features = {"text": {"_type": "Value", "dtype": "string"}, "bool_column": {"_type": "Value", "dtype": "bool"}}
    settings = _define_settings_from_features(features, feature_mapping={})

    assert len(settings.metadata) == 1
    assert isinstance(settings.metadata[0], ex.TermsMetadataProperty)
    assert settings.metadata[0].name == "bool_column"


def test_define_settings_from_features_multiple():
    features = {
        "text_column": {"_type": "Value", "dtype": "string"},
        "image_column": {"_type": "Image"},
        "label_column": {"_type": "ClassLabel", "names": ["A", "B"]},
    }
    settings = _define_settings_from_features(features, feature_mapping={})

    assert len(settings.fields) == 2
    assert isinstance(settings.fields[0], ex.TextField)
    assert settings.fields[0].name == "text_column"
    assert isinstance(settings.fields[1], ex.ImageField)
    assert settings.fields[1].name == "image_column"
    assert len(settings.questions) == 1
    assert isinstance(settings.questions[0], ex.LabelQuestion)
    assert settings.questions[0].name == "label_column"


def test_mapped_question():
    features = {
        "text_column": {"_type": "Value", "dtype": "string"},
        "image_column": {"_type": "Image"},
        "label_column": {"_type": "ClassLabel", "names": ["A", "B"]},
    }
    settings = _define_settings_from_features(features, feature_mapping={"text_column": "question"})

    assert len(settings.fields) == 1
    assert isinstance(settings.fields[0], ex.ImageField)
    assert settings.fields[0].name == "image_column"
    assert len(settings.questions) == 2
    assert isinstance(settings.questions[0], ex.TextQuestion)
    assert settings.questions[0].name == "text_column"
    assert isinstance(settings.questions[1], ex.LabelQuestion)
    assert settings.questions[1].name == "label_column"


def test_mapped_fields():
    features = {
        "text_column": {"_type": "Value", "dtype": "string"},
        "image_column": {"_type": "Image"},
        "label_column": {"_type": "ClassLabel", "names": ["A", "B"]},
    }
    settings = _define_settings_from_features(features, feature_mapping={"text_column": "field"})

    assert len(settings.fields) == 2
    assert isinstance(settings.fields[0], ex.TextField)
    assert settings.fields[0].name == "text_column"
    assert isinstance(settings.fields[1], ex.ImageField)
    assert settings.fields[1].name == "image_column"
    assert len(settings.questions) == 1
    assert isinstance(settings.questions[0], ex.LabelQuestion)
    assert settings.questions[0].name == "label_column"


def test_define_settings_from_features_unsupported():
    features = {
        "unsupported_column": {"_type": "Unsupported"},
        "text_field": {"_type": "Value", "dtype": "string"},
        "label_column": {"_type": "ClassLabel", "names": ["A", "B"]},
    }
    with pytest.warns(UserWarning, match="Feature 'unsupported_column' has an unsupported type"):
        settings = _define_settings_from_features(features, feature_mapping={})

    assert len(settings.fields) == 1
    assert len(settings.questions) == 1


def test_define_settings_from_only_label_raises():
    features = {"label_column": {"_type": "ClassLabel", "names": ["A", "B", "C"]}}

    with pytest.raises(SettingsError):
        _define_settings_from_features(features, feature_mapping={})
