"""Test API to query subjects from the graph database who match user-specified criteria."""

import pytest
from fastapi import HTTPException

from app.api import crud


def test_get_subjects_by_query(monkeypatch):
    """Test that graph results for dataset size queries are correctly parsed into a dictionary."""

    def mock_post_query_to_graph(query, timeout=5.0):
        return {
            "head": {"vars": ["dataset_uuid", "total_subjects"]},
            "results": {
                "bindings": [
                    {
                        "dataset_uuid": {
                            "type": "uri",
                            "value": "http://neurobagel.org/vocab/ds1234",
                        },
                        "total_subjects": {
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                            "type": "literal",
                            "value": "70",
                        },
                    },
                    {
                        "dataset_uuid": {
                            "type": "uri",
                            "value": "http://neurobagel.org/vocab/ds2345",
                        },
                        "total_subjects": {
                            "datatype": "http://www.w3.org/2001/XMLSchema#integer",
                            "type": "literal",
                            "value": "40",
                        },
                    },
                ]
            },
        }

    monkeypatch.setattr(crud, "post_query_to_graph", mock_post_query_to_graph)
    assert crud.query_matching_dataset_sizes(
        [
            "http://neurobagel.org/vocab/ds1234",
            "http://neurobagel.org/vocab/ds2345",
        ]
    ) == {
        "http://neurobagel.org/vocab/ds1234": 70,
        "http://neurobagel.org/vocab/ds2345": 40,
    }


def test_null_modalities(test_app, mock_post_query_to_graph, monkeypatch):
    """Given a response containing a dataset with no recorded modalities, returns an empty list for the imaging modalities."""

    def mock_query_matching_dataset_sizes(dataset_uuids):
        return {
            "http://neurobagel.org/vocab/12345": 200,
        }

    monkeypatch.setattr(crud, "post_query_to_graph", mock_post_query_to_graph)
    monkeypatch.setattr(
        crud, "query_matching_dataset_sizes", mock_query_matching_dataset_sizes
    )

    response = test_app.get("/query/")
    assert response.json()[0]["image_modals"] == [
        "http://purl.org/nidash/nidm#T1Weighted"
    ]


def test_get_all(test_app, mock_successful_get, monkeypatch):
    """Given no input for any query parameters, returns a 200 status code and a non-empty list of results (should correspond to all subjects in graph)."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get("/query/")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "valid_min_age, valid_max_age",
    [(30.5, 60), (23, 23)],
)
def test_get_valid_age_range(
    test_app, mock_successful_get, valid_min_age, valid_max_age, monkeypatch
):
    """Given a valid age range, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?min_age={valid_min_age}&max_age={valid_max_age}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize(
    "age_keyval",
    ["min_age=20.75", "max_age=50"],
)
def test_get_valid_age_single_bound(
    test_app, mock_successful_get, age_keyval, monkeypatch
):
    """Given only a valid lower/upper age bound, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?{age_keyval}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
@pytest.mark.parametrize(
    "invalid_min_age, invalid_max_age",
    [
        ("forty", "fifty"),
        (33, 21),
        (-42.5, -40),
    ],
)
def test_get_invalid_age(
    test_app, mock_get, invalid_min_age, invalid_max_age, monkeypatch
):
    """Given an invalid age range, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        f"/query/?min_age={invalid_min_age}&max_age={invalid_max_age}"
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "valid_sex",
    ["snomed:248153007", "snomed:248152002", "snomed:32570681000036106"],
)
def test_get_valid_sex(test_app, mock_successful_get, valid_sex, monkeypatch):
    """Given a valid sex string, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?sex={valid_sex}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
def test_get_invalid_sex(test_app, mock_get, monkeypatch):
    """Given an invalid sex string, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get("/query/?sex=apple")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "valid_diagnosis", ["snomed:35489007", "snomed:49049000"]
)
def test_get_valid_diagnosis(
    test_app, mock_successful_get, valid_diagnosis, monkeypatch
):
    """Given a valid diagnosis, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?diagnosis={valid_diagnosis}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
@pytest.mark.parametrize(
    "invalid_diagnosis", ["sn0med:35489007", "apple", ":123456"]
)
def test_get_invalid_diagnosis(
    test_app, mock_get, invalid_diagnosis, monkeypatch
):
    """Given an invalid diagnosis, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(f"/query/?diagnosis={invalid_diagnosis}")
    assert response.status_code == 422


@pytest.mark.parametrize("valid_iscontrol", [True, False])
def test_get_valid_iscontrol(
    test_app, mock_successful_get, valid_iscontrol, monkeypatch
):
    """Given a valid is_control value, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(f"/query/?is_control={valid_iscontrol}")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
def test_get_invalid_iscontrol(test_app, mock_get, monkeypatch):
    """Given a non-boolean is_control value, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get("/query/?is_control=apple")
    assert response.status_code == 422


@pytest.mark.parametrize("mock_get", [None], indirect=True)
def test_get_invalid_control_diagnosis_pair(test_app, mock_get, monkeypatch):
    """Given a non-default diagnosis value and is_control value of True, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        "/query/?diagnosis=snomed:35489007&is_control=True"
    )
    assert response.status_code == 422
    assert (
        "Subjects cannot both be healthy controls and have a diagnosis"
        in response.text
    )


# NOTE: Stacked parametrization is a feature of pytest: all combinations of the parameters are tested.
@pytest.mark.parametrize(
    "session_param",
    ["min_num_phenotypic_sessions", "min_num_imaging_sessions"],
)
@pytest.mark.parametrize("valid_min_num_sessions", [0, 1, 2, 4, 7])
def test_get_valid_min_num_sessions(
    test_app,
    mock_successful_get,
    session_param,
    valid_min_num_sessions,
    monkeypatch,
):
    """Given a valid minimum number of imaging sessions, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?{session_param}={valid_min_num_sessions}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
@pytest.mark.parametrize(
    "session_param",
    ["min_num_phenotypic_sessions", "min_num_imaging_sessions"],
)
@pytest.mark.parametrize("invalid_min_num_sessions", [-3, 2.5, "apple"])
def test_get_invalid_min_num_sessions(
    test_app,
    mock_get,
    session_param,
    invalid_min_num_sessions,
    monkeypatch,
):
    """Given an invalid minimum number of imaging sessions, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        f"/query/?{session_param}={invalid_min_num_sessions}"
    )
    response.status_code = 422


def test_get_valid_assessment(test_app, mock_successful_get, monkeypatch):
    """Given a valid assessment, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get("/query/?assessment=nb:cogAtlas-1234")
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
@pytest.mark.parametrize(
    "invalid_assessment", ["bg01:cogAtlas-1234", "cogAtlas-1234"]
)
def test_get_invalid_assessment(
    test_app, mock_get, invalid_assessment, monkeypatch
):
    """Given an invalid assessment, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(f"/query/?assessment={invalid_assessment}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "valid_available_image_modal",
    [
        "nidm:DiffusionWeighted",
        "nidm:EEG",
        "nidm:FlowWeighted",
        "nidm:T1Weighted",
        "nidm:T2Weighted",
    ],
)
def test_get_valid_available_image_modal(
    test_app, mock_successful_get, valid_available_image_modal, monkeypatch
):
    """Given a valid and available image modality, returns a 200 status code and a non-empty list of results."""

    monkeypatch.setattr(crud, "get", mock_successful_get)
    response = test_app.get(
        f"/query/?image_modal={valid_available_image_modal}"
    )
    assert response.status_code == 200
    assert response.json() != []


@pytest.mark.parametrize("mock_get", [[]], indirect=True)
@pytest.mark.parametrize(
    "valid_unavailable_image_modal",
    ["nidm:Flair", "owl:sameAs", "nb:FlowWeighted", "snomed:something"],
)
def test_get_valid_unavailable_image_modal(
    test_app, valid_unavailable_image_modal, mock_get, monkeypatch
):
    """Given a valid, pre-defined, and unavailable image modality, returns a 200 status code and an empty list of results."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(
        f"/query/?image_modal={valid_unavailable_image_modal}"
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("mock_get", [None], indirect=True)
@pytest.mark.parametrize(
    "invalid_image_modal", ["2nim:EEG", "apple", "some_thing:cool"]
)
def test_get_invalid_image_modal(
    test_app, mock_get, invalid_image_modal, monkeypatch
):
    """Given an invalid image modality, returns a 422 status code."""

    monkeypatch.setattr(crud, "get", mock_get)
    response = test_app.get(f"/query/?image_modal={invalid_image_modal}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "mock_get_with_exception", [HTTPException(500)], indirect=True
)
@pytest.mark.parametrize(
    "undefined_prefix_image_modal",
    ["dbo:abstract", "sex:apple", "something:cool"],
)
def test_get_undefined_prefix_image_modal(
    test_app,
    undefined_prefix_image_modal,
    mock_get_with_exception,
    monkeypatch,
):
    """Given a valid and undefined prefix image modality, returns a 500 status code."""

    monkeypatch.setattr(crud, "get", mock_get_with_exception)
    response = test_app.get(
        f"/query/?image_modal={undefined_prefix_image_modal}"
    )
    assert response.status_code == 500
