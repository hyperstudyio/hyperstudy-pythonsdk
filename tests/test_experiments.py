"""Tests for experiment CRUD methods."""

from __future__ import annotations

import json

import responses

from hyperstudy import (
    Experiment,
    HyperStudy,
    Role,
    State,
    show_text,
)
from hyperstudy._display import ExperimentInfo
from hyperstudy.exceptions import NotFoundError

import pytest

BASE_URL = "https://api.hyperstudy.io/api/v3"


@responses.activate
def test_list_experiments(experiments_list_response):
    """list_experiments returns a DataFrame of experiments."""
    responses.get(
        f"{BASE_URL}/experiments",
        json=experiments_list_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    df = client.list_experiments(limit=50)

    assert len(df) == 2
    assert "name" in df.columns
    assert df["name"].iloc[0] == "Emotion Study"


@responses.activate
def test_list_experiments_dict(experiments_list_response):
    """list_experiments with output='dict' returns list of dicts."""
    responses.get(
        f"{BASE_URL}/experiments",
        json=experiments_list_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    data = client.list_experiments(limit=50, output="dict")

    assert isinstance(data, list)
    assert data[0]["id"] == "exp_abc123"


@responses.activate
def test_get_experiment(experiment_single_response):
    """get_experiment returns an ExperimentInfo object."""
    responses.get(
        f"{BASE_URL}/experiments/exp_abc123",
        json=experiment_single_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    exp = client.get_experiment("exp_abc123")

    assert isinstance(exp, ExperimentInfo)
    assert exp["id"] == "exp_abc123"
    assert exp["name"] == "Emotion Study"
    assert "Emotion Study" in repr(exp)


@responses.activate
def test_get_experiment_repr_html(experiment_single_response):
    """ExperimentInfo has _repr_html_ for notebooks."""
    responses.get(
        f"{BASE_URL}/experiments/exp_abc123",
        json=experiment_single_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    exp = client.get_experiment("exp_abc123")

    html = exp._repr_html_()
    assert "Emotion Study" in html
    assert "<table" in html


@responses.activate
def test_get_experiment_config(experiment_single_response):
    """get_experiment_config returns a plain dict."""
    responses.get(
        f"{BASE_URL}/experiments/exp_abc123/config",
        json=experiment_single_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    config = client.get_experiment_config("exp_abc123")

    assert isinstance(config, dict)
    assert config["id"] == "exp_abc123"


@responses.activate
def test_create_experiment():
    """create_experiment POSTs to the experiments endpoint."""
    create_response = {
        "status": "success",
        "metadata": {"dataType": "experiment", "scope": "experiment", "scopeId": "exp_new"},
        "data": [{"id": "exp_new", "name": "New Study", "createdAt": "2024-06-15T10:00:00Z"}],
    }
    responses.post(
        f"{BASE_URL}/experiments",
        json=create_response,
        status=201,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    exp = client.create_experiment(name="New Study", description="Test")

    assert isinstance(exp, ExperimentInfo)
    assert exp["id"] == "exp_new"

    # Verify request body
    import json
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "New Study"
    assert body["description"] == "Test"


@responses.activate
def test_update_experiment():
    """update_experiment PUTs to the correct endpoint."""
    update_response = {
        "status": "success",
        "metadata": {"dataType": "experiment", "scope": "experiment", "scopeId": "exp_abc123"},
        "data": [{"id": "exp_abc123", "updated": True}],
    }
    responses.put(
        f"{BASE_URL}/experiments/exp_abc123",
        json=update_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    result = client.update_experiment("exp_abc123", name="Updated Name")

    assert result["updated"] is True

    import json
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "Updated Name"


@responses.activate
def test_delete_experiment():
    """delete_experiment sends DELETE to the correct endpoint."""
    delete_response = {
        "status": "success",
        "metadata": {"dataType": "experiment", "scope": "experiment", "scopeId": "exp_abc123"},
        "data": [{"id": "exp_abc123", "deleted": True}],
    }
    responses.delete(
        f"{BASE_URL}/experiments/exp_abc123",
        json=delete_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    client.delete_experiment("exp_abc123")

    assert len(responses.calls) == 1
    assert "skipDataCheck" not in responses.calls[0].request.url


@responses.activate
def test_delete_experiment_skip_data_check():
    """delete_experiment with skip_data_check passes query param."""
    delete_response = {
        "status": "success",
        "metadata": {"dataType": "experiment"},
        "data": [{"id": "exp_abc123", "deleted": True}],
    }
    responses.delete(
        f"{BASE_URL}/experiments/exp_abc123",
        json=delete_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    client.delete_experiment("exp_abc123", skip_data_check=True)

    assert "skipDataCheck=true" in responses.calls[0].request.url


@responses.activate
def test_create_experiment_with_builder():
    """Passing an Experiment object posts the snake→camel-converted payload."""
    create_response = {
        "status": "success",
        "metadata": {"dataType": "experiment", "scope": "experiment", "scopeId": "exp_b"},
        "data": [{"id": "exp_b", "name": "Builder Study"}],
    }
    responses.post(
        f"{BASE_URL}/experiments",
        json=create_response,
        status=201,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    exp = Experiment(
        name="Builder Study",
        required_participants=2,
        states=[State(id="s1", focus_component=show_text("Hi", id="ft1"))],
        roles={"speaker": Role(name="Speaker", participant_count=1)},
    )
    info = client.create_experiment(experiment=exp)

    assert isinstance(info, ExperimentInfo)
    assert info["id"] == "exp_b"

    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "name": "Builder Study",
        "requiredParticipants": 2,
        "states": [
            {
                "id": "s1",
                "focusComponent": {
                    "type": "showtext",
                    "config": {"text": "Hi"},
                    "id": "ft1",
                },
            }
        ],
        "roles": {"speaker": {"name": "Speaker", "participantCount": 1}},
    }


@responses.activate
def test_create_experiment_kwarg_overrides_builder():
    """Explicit kwargs win when both `experiment=` and `**kwargs` are given."""
    create_response = {
        "status": "success",
        "metadata": {"dataType": "experiment"},
        "data": [{"id": "exp_o", "name": "Override"}],
    }
    responses.post(
        f"{BASE_URL}/experiments",
        json=create_response,
        status=201,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    client.create_experiment(
        experiment=Experiment(name="Original"),
        name="Override",
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "Override"


def test_create_experiment_requires_name():
    """create_experiment raises TypeError when neither name nor experiment supplied."""
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    with pytest.raises(TypeError, match="requires a 'name'"):
        client.create_experiment()


@responses.activate
def test_update_experiment_with_builder():
    """update_experiment accepts an Experiment object."""
    update_response = {
        "status": "success",
        "metadata": {"dataType": "experiment"},
        "data": [{"id": "exp_abc123", "updated": True}],
    }
    responses.put(
        f"{BASE_URL}/experiments/exp_abc123",
        json=update_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    client.update_experiment(
        "exp_abc123",
        experiment=Experiment(name="Renamed", description="New desc"),
    )

    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Renamed", "description": "New desc"}


@responses.activate
def test_validate_experiment():
    """validate_experiment POSTs to /experiments/validate."""
    validate_response = {
        "status": "success",
        "metadata": {"dataType": "experiment"},
        "data": [{"valid": True}],
    }
    responses.post(
        f"{BASE_URL}/experiments/validate",
        json=validate_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    result = client.validate_experiment(Experiment(name="Check me"))

    assert result == {"valid": True}
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Check me"}


def test_validate_experiment_rejects_none():
    """validate_experiment(None) raises rather than silently POSTing an empty body."""
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    with pytest.raises(TypeError, match="requires an Experiment or dict"):
        client.validate_experiment(None)  # type: ignore[arg-type]


def test_build_payload_rejects_non_dict_non_model():
    """_build_experiment_payload rejects unsupported types instead of silently dict()ing them."""
    from hyperstudy.experiments import _build_experiment_payload

    with pytest.raises(TypeError, match="must be an Experiment or dict"):
        _build_experiment_payload("not a dict")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be an Experiment or dict"):
        _build_experiment_payload([("name", "x")])  # type: ignore[arg-type]


def test_update_experiment_experiment_is_keyword_only():
    """`experiment=` must be a keyword arg — second positional should raise."""
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    with pytest.raises(TypeError):
        client.update_experiment("exp_id", Experiment(name="x"))  # type: ignore[misc]


def test_create_experiment_experiment_is_keyword_only():
    """`experiment=` must be a keyword arg in create_experiment too."""
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    with pytest.raises(TypeError):
        client.create_experiment(Experiment(name="x"))  # type: ignore[misc]


@responses.activate
def test_validate_experiment_accepts_raw_dict():
    """validate_experiment also accepts a plain dict."""
    validate_response = {
        "status": "success",
        "metadata": {"dataType": "experiment"},
        "data": [{"valid": False, "errors": ["x"]}],
    }
    responses.post(
        f"{BASE_URL}/experiments/validate",
        json=validate_response,
        status=200,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    result = client.validate_experiment({"name": "raw dict"})

    assert result == {"valid": False, "errors": ["x"]}


@responses.activate
def test_get_experiment_not_found():
    """404 raises NotFoundError."""
    error_response = {
        "status": "error",
        "error": {"code": "NOT_FOUND", "message": "Experiment not found"},
    }
    responses.get(
        f"{BASE_URL}/experiments/exp_nonexistent",
        json=error_response,
        status=404,
    )
    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    with pytest.raises(NotFoundError, match="not found"):
        client.get_experiment("exp_nonexistent")
