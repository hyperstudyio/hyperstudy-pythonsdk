"""Voice conversations, the component/participant/room filters, and data-access checks."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pandas as pd
import responses

from hyperstudy import DataType, HyperStudy

from .conftest import BASE_URL, envelope

UTTERANCE = {
    "eventId": "ev1", "roomId": "room_1", "participantId": "p_human",
    "kind": "utterance", "speaker": "participant", "timestamp": "2026-10-20T15:00:01.000Z",
    "onset": 1000, "transcript": "Hi there", "transcriptionStatus": "completed",
}
AGENT_REPLY = {
    "eventId": "ev2", "roomId": "room_1", "participantId": "p_agent",
    "kind": "utterance", "speaker": "agent", "timestamp": "2026-10-20T15:00:02.500Z",
    "onset": 2500, "transcript": "Hello! How are you?", "heardMs": 1800, "generatedMs": 1800,
    "truncated": False, "responseLatencyMs": 640,
}
CONTEXT = {
    "eventId": "ev3", "roomId": "room_1", "participantId": "p_agent",
    "kind": "context", "speaker": "engine", "timestamp": "2026-10-20T15:00:00.000Z",
    "onset": 0, "contextKind": "screen", "contextText": "Rate the video",
}


def _page(rows, *, total, offset, limit=1000):
    body = envelope(rows, dataType="voice")
    has_more = offset + len(rows) < total
    body["metadata"]["pagination"] = {
        "total": total, "returned": len(rows), "limit": limit, "offset": offset,
        "hasMore": has_more, "nextOffset": offset + limit if has_more else None,
    }
    return body


def _query(call_index: int = 0) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(responses.calls[call_index].request.url).query).items()}


@responses.activate
def test_get_voice_room_conversation(api_key):
    responses.get(
        f"{BASE_URL}/data/voice/room/room_1",
        json=_page([CONTEXT, UTTERANCE, AGENT_REPLY], total=3, offset=0),
    )
    df = HyperStudy(api_key=api_key).get_voice("room_1", scope="room")

    assert isinstance(df, pd.DataFrame)
    assert list(df["kind"]) == ["context", "utterance", "utterance"]
    assert list(df["speaker"]) == ["engine", "participant", "agent"]
    assert df.iloc[2]["responseLatencyMs"] == 640
    # Context rows are included unless asked otherwise: no parameter sent.
    assert "includeContext" not in _query()


@responses.activate
def test_get_voice_paginates(api_key):
    url = f"{BASE_URL}/data/voice/experiment/exp_1"
    responses.get(url, json=_page([UTTERANCE], total=2, offset=0, limit=1))
    responses.get(url, json=_page([AGENT_REPLY], total=2, offset=1, limit=1))

    df = HyperStudy(api_key=api_key).get_voice("exp_1", progress=False)

    assert list(df["eventId"]) == ["ev1", "ev2"]
    assert _query(1)["offset"] == "1"


@responses.activate
def test_get_voice_filters(api_key):
    responses.get(f"{BASE_URL}/data/voice/experiment/exp_1", json=_page([], total=0, offset=0))
    responses.get(f"{BASE_URL}/data/voice/participant/p_human", json=_page([], total=0, offset=0))
    client = HyperStudy(api_key=api_key)

    client.get_voice("exp_1", deployment_id="dep_1", include_context=False, order="desc")
    client.get_voice("p_human", scope="participant", room_id="room_1")

    assert _query(0) == {
        "deploymentId": "dep_1", "includeContext": "false", "order": "desc", "limit": "1000", "offset": "0",
    }
    assert _query(1)["roomId"] == "room_1"


def test_voice_data_type():
    assert DataType.VOICE == "voice"


@responses.activate
def test_get_components_filters(api_key):
    responses.get(f"{BASE_URL}/data/components/room/room_1", json=_page([], total=0, offset=0))
    HyperStudy(api_key=api_key).get_components(
        "room_1", scope="room", component_type="vasrating", state_id="state_3", completed=True,
        start_time="2026-10-20T00:00:00Z", end_time="2026-10-21T00:00:00Z", sort="timestamp", order="asc",
    )
    query = _query()
    assert query["componentType"] == "vasrating"
    assert query["stateId"] == "state_3"
    assert query["completed"] == "true"
    assert query["startTime"] == "2026-10-20T00:00:00Z"
    assert query["endTime"] == "2026-10-21T00:00:00Z"
    assert (query["sort"], query["order"]) == ("timestamp", "asc")


@responses.activate
def test_get_components_completed_false_is_sent(api_key):
    responses.get(f"{BASE_URL}/data/components/experiment/exp_1", json=_page([], total=0, offset=0))
    HyperStudy(api_key=api_key).get_components("exp_1", completed=False)
    assert _query()["completed"] == "false"


@responses.activate
def test_get_participants_and_rooms_filters(api_key):
    responses.get(f"{BASE_URL}/data/participants/experiment/exp_1", json=_page([], total=0, offset=0))
    responses.get(f"{BASE_URL}/data/rooms/experiment/exp_1", json=_page([], total=0, offset=0))
    client = HyperStudy(api_key=api_key)

    client.get_participants("exp_1", completion_code="ABANDONED", sort="createdAt", order="desc")
    client.get_rooms("exp_1", sort="createdAt", order="asc")

    participants = _query(0)
    assert participants["completionCode"] == "ABANDONED"
    assert (participants["sort"], participants["order"]) == ("createdAt", "desc")
    assert (_query(1)["sort"], _query(1)["order"]) == ("createdAt", "asc")


@responses.activate
def test_check_data_access(api_key):
    # This endpoint answers at the top level, not in the data envelope.
    responses.get(
        f"{BASE_URL}/data/check-access/experiment/exp_1",
        json={"status": "success", "canView": True, "canExport": False},
    )
    access = HyperStudy(api_key=api_key).check_data_access("exp_1")
    assert access == {"canView": True, "canExport": False}
