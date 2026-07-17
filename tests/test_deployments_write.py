"""Tests for the agent-deployment write methods."""

from __future__ import annotations

import json

import pytest
import responses

from hyperstudy import HyperStudy
from hyperstudy.exceptions import ValidationError

from .conftest import BASE_URL


@pytest.fixture
def api_key():
    return "hst_test_abc123"


def _envelope(data):
    return {"status": "success", "data": data, "metadata": {}}


@responses.activate
def test_create_deployment_agent_only(api_key):
    responses.post(
        f"{BASE_URL}/deployments",
        json=_envelope({"id": "dep-1", "type": "agent-only", "status": "active"}),
        status=201,
    )

    client = HyperStudy(api_key=api_key)
    dep = client.create_deployment(
        "exp-1",
        config={"name": "Pilot", "type": "agent-only", "agentDeployment": {"rooms": 3, "budgetUsd": 5}},
    )

    assert dep["id"] == "dep-1"
    sent = json.loads(responses.calls[0].request.body)
    assert sent["experimentId"] == "exp-1"
    assert sent["config"]["agentDeployment"]["rooms"] == 3


@responses.activate
def test_create_deployment_preflight_failure_raises_validation_error(api_key):
    responses.post(
        f"{BASE_URL}/deployments",
        json={
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Agent role preflight failed",
                "details": {"errors": [{"role": "a", "reason": "missing provider key"}]},
            },
        },
        status=400,
    )

    client = HyperStudy(api_key=api_key)
    with pytest.raises(ValidationError):
        client.create_deployment("exp-1", config={"type": "agent-only"})


@responses.activate
def test_run_more_and_spend_and_room_controls(api_key):
    responses.post(
        f"{BASE_URL}/deployments/dep-1/run-more",
        json=_envelope({"batchId": "batch_1", "requestedRooms": 2}),
        status=202,
    )
    responses.get(
        f"{BASE_URL}/deployments/dep-1/agent-spend",
        json=_envelope({"total": 1.5, "perRoom": {"room-1": 1.5}}),
        status=200,
    )
    responses.post(
        f"{BASE_URL}/deployments/dep-1/rooms/room-1/stop",
        json=_envelope({"stopped": True}),
        status=200,
    )
    responses.post(
        f"{BASE_URL}/deployments/dep-1/rooms/room-1/retry",
        json=_envelope({"batchId": "batch_2", "requestedRooms": 1}),
        status=202,
    )

    client = HyperStudy(api_key=api_key)

    batch = client.run_more("dep-1", rooms=2, budget_usd=3.0)
    assert batch["batchId"] == "batch_1"
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"rooms": 2, "budgetUsd": 3.0}

    spend = client.get_agent_spend("dep-1")
    assert spend["total"] == 1.5

    client.stop_room("dep-1", "room-1")

    retry = client.retry_room("dep-1", "room-1")
    assert retry["requestedRooms"] == 1
