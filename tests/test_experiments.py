"""Tests for experiment CRUD methods."""

from __future__ import annotations

import responses

from hyperstudy import HyperStudy
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
