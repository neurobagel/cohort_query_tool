"""Test API endpoints for querying controlled terms and vocabularies."""

import httpx
import pytest

from app.api import crud
from app.api import utility as util


@pytest.mark.parametrize(
    "valid_data_element_URI",
    ["nb:Diagnosis", "nb:Assessment"],
)
def test_get_terms_valid_data_element_URI(
    test_app, mock_successful_get_terms, valid_data_element_URI, monkeypatch
):
    """Given a valid data element URI, returns a 200 status code and a non-empty list of terms for that data element."""

    monkeypatch.setattr(crud, "get_terms", mock_successful_get_terms)
    response = test_app.get(f"/attributes/{valid_data_element_URI}")
    assert response.status_code == 200
    first_key = next(iter(response.json()))
    assert response.json()[first_key] != []


@pytest.mark.parametrize(
    "invalid_data_element_URI",
    ["apple", "some_thing:cool"],
)
def test_get_terms_invalid_data_element_URI(
    test_app, invalid_data_element_URI
):
    """Given an invalid data element URI, returns a 422 status code as the validation of the data element URI fails."""

    response = test_app.get(f"/attributes/{invalid_data_element_URI}")
    assert response.status_code == 422


def test_get_terms_for_attribute_with_vocab_lookup(test_app, monkeypatch):
    """
    Given a valid data element URI with a vocabulary lookup file available, returns prefixed term URIs and their human-readable labels (where found)
    for instances of that data element, and excludes terms with unrecognized namespaces with an informative warning.
    """
    monkeypatch.setenv(util.GRAPH_USERNAME.name, "SomeUser")
    monkeypatch.setenv(util.GRAPH_PASSWORD.name, "SomePassword")

    # TODO: Since these mock HTTPX response JSONs are so similar (and useful), refactor their creation out into a function.
    mock_response_json = {
        "head": {"vars": ["termURL"]},
        "results": {
            "bindings": [
                {
                    "termURL": {
                        "type": "uri",
                        "value": "https://www.cognitiveatlas.org/task/id/tsk_U9gDp8utahAfO",
                    }
                },
                {
                    "termURL": {
                        "type": "uri",
                        "value": "https://www.cognitiveatlas.org/task/id/not_found_id",
                    }
                },
                {
                    "termURL": {
                        "type": "uri",
                        "value": "https://www.notanatlas.org/task/id/tsk_alz5hjlUXp4WY",
                    }
                },
            ]
        },
    }

    def mock_httpx_post(**kwargs):
        return httpx.Response(status_code=200, json=mock_response_json)

    monkeypatch.setattr(httpx, "post", mock_httpx_post)

    with pytest.warns(
        UserWarning,
        match="does not come from a vocabulary recognized by Neurobagel",
    ):
        with test_app:
            response = test_app.get("/attributes/nb:Assessment")

    assert response.json() == {
        "nb:Assessment": [
            {
                "TermURL": "cogatlas:tsk_U9gDp8utahAfO",
                "Label": "Pittsburgh Stress Battery",
            },
            {"TermURL": "cogatlas:not_found_id", "Label": None},
        ]
    }


def test_get_terms_for_attribute_without_vocab_lookup(test_app, monkeypatch):
    """
    Given a valid data element URI without any vocabulary lookup file available, returns prefixed term URIs and  instances of that data element, and excludes terms with unrecognized namespaces with an informative warning.
    """
    monkeypatch.setenv(util.GRAPH_USERNAME.name, "SomeUser")
    monkeypatch.setenv(util.GRAPH_PASSWORD.name, "SomePassword")
    # Create a mock context with some fake ontologies (with no vocabulary lookup files)
    monkeypatch.setattr(
        util,
        "CONTEXT",
        {
            "cko": "https://www.coolknownontology.org/task/id/",
            "ako": "https://www.awesomeknownontology.org/vocab/",
        },
    )

    mock_response_json = {
        "head": {"vars": ["termURL"]},
        "results": {
            "bindings": [
                {
                    "termURL": {
                        "type": "uri",
                        "value": "https://www.coolknownontology.org/task/id/trm_123",
                    }
                },
                {
                    "termURL": {
                        "type": "uri",
                        "value": "https://www.coolknownontology.org/task/id/trm_234",
                    }
                },
            ]
        },
    }

    def mock_httpx_post(**kwargs):
        return httpx.Response(status_code=200, json=mock_response_json)

    monkeypatch.setattr(httpx, "post", mock_httpx_post)

    response = test_app.get("/attributes/nb:SomeClass")

    assert response.json() == {
        "nb:SomeClass": [
            {"TermURL": "cko:trm_123", "Label": None},
            {"TermURL": "cko:trm_234", "Label": None},
        ]
    }


def test_get_attributes(
    test_app,
    monkeypatch,
):
    """Given a GET request to the /attributes/ endpoint, successfully returns controlled term attributes with namespaces abbrieviated and as a list."""

    monkeypatch.setenv(util.GRAPH_USERNAME.name, "SomeUser")
    monkeypatch.setenv(util.GRAPH_PASSWORD.name, "SomePassword")

    mock_response_json = {
        "head": {"vars": ["attribute"]},
        "results": {
            "bindings": [
                {
                    "attribute": {
                        "type": "uri",
                        "value": "http://neurobagel.org/vocab/ControlledTerm1",
                    }
                },
                {
                    "attribute": {
                        "type": "uri",
                        "value": "http://neurobagel.org/vocab/ControlledTerm2",
                    }
                },
                {
                    "attribute": {
                        "type": "uri",
                        "value": "http://neurobagel.org/vocab/ControlledTerm3",
                    }
                },
            ]
        },
    }

    def mock_httpx_post(**kwargs):
        return httpx.Response(status_code=200, json=mock_response_json)

    monkeypatch.setattr(httpx, "post", mock_httpx_post)
    response = test_app.get("/attributes/")

    assert response.json() == [
        "nb:ControlledTerm1",
        "nb:ControlledTerm2",
        "nb:ControlledTerm3",
    ]


def test_get_attribute_vocab(test_app, monkeypatch):
    """Given a GET request to the /attributes/{data_element_URI}/vocab endpoint, successfully returns a JSON object containing the vocabulary name, namespace info, and term-label mappings."""
    monkeypatch.setenv(util.GRAPH_USERNAME.name, "SomeUser")
    monkeypatch.setenv(util.GRAPH_PASSWORD.name, "SomePassword")
    mock_term_labels = {
        "tsk_p7cabUkVvQPBS": "Generalized Self-Efficacy Scale",
        "tsk_ccTKYnmv7tOZY": "Verbal Interference Test",
    }

    def mock_load_json(path):
        return mock_term_labels

    monkeypatch.setattr(util, "load_json", mock_load_json)
    response = test_app.get("/attributes/nb:Assessment/vocab")

    assert response.status_code == 200
    assert response.json() == {
        "vocabulary_name": "Cognitive Atlas Tasks",
        "namespace_url": util.CONTEXT["cogatlas"],
        "namespace_prefix": "cogatlas",
        "term_labels": mock_term_labels,
    }
