"""Fields whose keys must reach the server exactly as written.

Snake_case → camelCase conversion is right for the SDK's own schema fields,
but some fields carry keys that belong to someone else: a provider's raw
request params, the voice engine's turn-detection settings, names the
researcher chose (cognition contexts, stimulus mappings), and the two
Prolific fields the backend stores in snake_case. Converting those keys
silently changes what the server stores or makes it reject the request.
"""

from __future__ import annotations

import json

import responses

from hyperstudy import HyperStudy

from .conftest import BASE_URL, envelope


def _sent(call_index: int = 0) -> dict:
    return json.loads(responses.calls[call_index].request.body)


@responses.activate
def test_persona_extra_params_keep_provider_keys(api_key):
    responses.post(f"{BASE_URL}/personas", json=envelope({"id": "p1"}), status=201)
    HyperStudy(api_key=api_key).create_persona(
        name="Custom",
        provider="custom",
        extra_params={"top_k": 20, "chat_template_kwargs": {"enable_thinking": False}},
    )
    assert _sent()["extraParams"] == {"top_k": 20, "chat_template_kwargs": {"enable_thinking": False}}


@responses.activate
def test_persona_cognition_keeps_context_names(api_key):
    responses.post(f"{BASE_URL}/personas", json=envelope({"id": "p1"}), status=201)
    cognition = {"config": {"contexts": {"post_trial": {"memory": None}}}}
    HyperStudy(api_key=api_key).create_persona(name="Thinker", cognition=cognition)
    assert _sent()["cognition"] == cognition


@responses.activate
def test_experiment_engine_turn_detection_keeps_engine_keys(api_key):
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        agent_config={
            "voice_turn_taking": {
                "min_response_delay_ms": 200,
                "engine_turn_detection": {"type": "server_vad", "silence_duration_ms": 800, "prefix_padding_ms": 300},
            }
        },
    )
    turn_taking = _sent()["agentConfig"]["voiceTurnTaking"]
    assert turn_taking["minResponseDelayMs"] == 200
    assert turn_taking["engineTurnDetection"] == {
        "type": "server_vad", "silence_duration_ms": 800, "prefix_padding_ms": 300,
    }


@responses.activate
def test_experiment_dict_engine_turn_detection_keeps_engine_keys(api_key):
    responses.post(f"{BASE_URL}/experiments", json=envelope({"id": "exp-1"}), status=201)
    HyperStudy(api_key=api_key).create_experiment(
        experiment={
            "name": "Voice study",
            "agent_config": {"voice_turn_taking": {"engine_turn_detection": {"type": "server_vad", "silence_duration_ms": 900}}},
        }
    )
    assert _sent()["agentConfig"]["voiceTurnTaking"]["engineTurnDetection"] == {"type": "server_vad", "silence_duration_ms": 900}


@responses.activate
def test_experiment_prolific_fields_stay_snake_case(api_key):
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1", prolific_enabled=True, prolific_config={"enabled": True}
    )
    sent = _sent()
    assert sent == {"prolific_enabled": True, "prolific_config": {"enabled": True}}


@responses.activate
def test_experiment_stimulus_mappings_keep_mapping_names(api_key):
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    mappings = {"face_set_a": {"happy_face": "https://cdn.example/a.png"}}
    HyperStudy(api_key=api_key).update_experiment("exp-1", stimulus_mappings=mappings)
    assert _sent()["stimulusMappings"] == mappings


@responses.activate
def test_schema_fields_are_still_camelized(api_key):
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1", waiting_room_config={"max_wait_time_ms": 5000}
    )
    assert _sent() == {"waitingRoomConfig": {"maxWaitTimeMs": 5000}}
