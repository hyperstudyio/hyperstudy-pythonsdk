"""Tests for agent data methods: decisions, decision detail, and runs."""

from __future__ import annotations

import warnings

import pandas as pd
import pytest
import responses

from hyperstudy import HyperStudy
from hyperstudy._types import DataType

from .conftest import BASE_URL, load_fixture


@pytest.fixture
def api_key():
    return "hst_test_abc123"


# ------------------------------------------------------------------
# get_agent_decisions
# ------------------------------------------------------------------


@responses.activate
def test_get_agent_decisions_experiment_scope(api_key):
    fixture = load_fixture("agent_decisions_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/experiment/exp_123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    df = client.get_agent_decisions("exp_123")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert set(df["_type"]) == {"decision", "run"}


@responses.activate
def test_get_agent_decisions_room_scope_builds_room_path(api_key):
    fixture = load_fixture("agent_decisions_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/room/room_abc123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    rows = client.get_agent_decisions("room_abc123", scope="room", output="dict")

    assert isinstance(rows, list)
    assert rows[0]["participantId"] == "agent_r1_p1"


@responses.activate
def test_get_agent_decisions_passes_detail_and_limit_params(api_key):
    fixture = load_fixture("agent_decisions_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/experiment/exp_123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    client.get_agent_decisions("exp_123", detail=True, limit=100, output="dict")

    request = responses.calls[0].request
    assert "detail=true" in request.url
    assert "limit=100" in request.url


@responses.activate
def test_get_agent_decisions_warns_on_truncation(api_key):
    fixture = load_fixture("agent_decisions_truncated_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/experiment/exp_123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    with pytest.warns(UserWarning, match="truncated"):
        client.get_agent_decisions("exp_123", output="dict")


@responses.activate
def test_get_agent_decisions_participant_filter(api_key):
    fixture = load_fixture("agent_decisions_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/room/room_abc123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    rows = client.get_agent_decisions(
        "room_abc123", scope="room", participant_id="agent_r1_p1", output="dict"
    )
    assert len(rows) == 3  # all fixture rows belong to agent_r1_p1

    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/room/room_abc123",
        json=fixture,
        status=200,
    )
    rows = client.get_agent_decisions(
        "room_abc123", scope="room", participant_id="someone_else", output="dict"
    )
    assert rows == []


def test_get_agent_decisions_rejects_bad_scope(api_key):
    client = HyperStudy(api_key=api_key)
    with pytest.raises(ValueError, match="scope"):
        client.get_agent_decisions("exp_123", scope="participant")


# ------------------------------------------------------------------
# get_agent_decision (single, detail)
# ------------------------------------------------------------------


@responses.activate
def test_get_agent_decision_detail(api_key):
    fixture = load_fixture("agent_decision_detail_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-decisions/room/room_abc123/decision/agent_r1_p1_2",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    decision = client.get_agent_decision("room_abc123", "agent_r1_p1_2")

    assert decision["id"] == "agent_r1_p1_2"
    assert decision["prompt"].startswith("You are")
    assert decision["chain"][0]["stage"] == "goal_infer"
    assert decision["predictionUpdate"]["predictionError"] == pytest.approx(0.18)


# ------------------------------------------------------------------
# get_agent_runs
# ------------------------------------------------------------------


@responses.activate
def test_get_agent_runs(api_key):
    fixture = load_fixture("agent_runs_response.json")
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/agent-runs/experiment/exp_123",
        json=fixture,
        status=200,
    )

    client = HyperStudy(api_key=api_key)
    df = client.get_agent_runs("exp_123")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert df[df["roomId"] == "room_def456"].iloc[0]["orphaned"]
    assert df.iloc[0]["totalCostUsd"] == pytest.approx(0.089)


# ------------------------------------------------------------------
# Enum entries
# ------------------------------------------------------------------


def test_datatype_enum_has_agent_entries():
    assert DataType.AGENT_DECISIONS == "agentDecisions"
    assert DataType.AGENT_RUNS == "agentRuns"
