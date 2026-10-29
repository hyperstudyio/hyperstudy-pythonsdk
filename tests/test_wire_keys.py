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


@responses.activate
def test_typed_models_passed_as_kwargs_are_serialized(api_key):
    """update_experiment(agent_config=AgentConfig(...)) and update_persona(voice=PersonaVoice(...))."""
    from hyperstudy import AgentConfig, EngineTurnDetection, PersonaVoice, RealtimeVoice, VoiceTurnTaking

    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    responses.put(f"{BASE_URL}/personas/p1", json=envelope({"id": "p1"}), status=200)
    client = HyperStudy(api_key=api_key)

    client.update_experiment(
        "exp-1",
        agent_config=AgentConfig(
            voice_turn_taking=VoiceTurnTaking(
                engine_turn_detection=EngineTurnDetection(type="server_vad", silence_duration_ms=800),
                min_response_delay_ms=250,
            )
        ),
    )
    client.update_persona(
        "p1", voice=PersonaVoice(engine="realtime", preset="marin", realtime=RealtimeVoice(provider="openai"))
    )

    assert _sent(0) == {
        "agentConfig": {
            "voiceTurnTaking": {
                "engineTurnDetection": {"type": "server_vad", "silence_duration_ms": 800},
                "minResponseDelayMs": 250,
            }
        }
    }
    assert _sent(1) == {"voice": {"engine": "realtime", "preset": "marin", "realtime": {"provider": "openai"}}}


@responses.activate
def test_user_named_keys_matching_verbatim_fields_are_still_converted(api_key):
    """A variable or role NAMED like a verbatim field is still a variable or role."""
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        variables={"metadata": {"initial_value": 1}, "score": {"initial_value": 0}},
        roles={"cognition": {"participant_count": 1}},
    )
    sent = _sent()
    assert sent["variables"] == {"metadata": {"initialValue": 1}, "score": {"initialValue": 0}}
    assert sent["roles"] == {"cognition": {"participantCount": 1}}


@responses.activate
def test_verbatim_fields_apply_only_where_they_are_defined(api_key):
    """`metadata` nested inside a component config is not the experiment's metadata."""
    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        metadata={"lab_notes": "kept"},
        states=[{"id": "s1", "focus_component": {"type": "showtext", "config": {"metadata": {"font_size": 3}}}}],
    )
    sent = _sent()
    assert sent["metadata"] == {"lab_notes": "kept"}
    assert sent["states"][0]["focusComponent"]["config"]["metadata"] == {"fontSize": 3}


def test_factory_config_extra_named_like_a_verbatim_field_is_converted():
    from hyperstudy import show_text

    component = show_text("Hello", metadata={"font_size": 3})
    assert component.config["metadata"] == {"fontSize": 3}


@responses.activate
def test_typed_model_inside_a_verbatim_field_is_serialized(api_key):
    from hyperstudy import EngineTurnDetection

    responses.put(f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1"}), status=200)
    HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        agent_config={"voice_turn_taking": {
            "engine_turn_detection": EngineTurnDetection(type="server_vad", silence_duration_ms=800),
        }},
    )
    assert _sent()["agentConfig"]["voiceTurnTaking"]["engineTurnDetection"] == {
        "type": "server_vad", "silence_duration_ms": 800,
    }


def test_models_module_exports_every_model():
    import hyperstudy
    import hyperstudy.models as models

    exported_models = {
        name for name in hyperstudy.__all__
        if isinstance(getattr(hyperstudy, name), type) and issubclass(getattr(hyperstudy, name), models.BaseModel)
    }
    assert exported_models <= set(models.__all__)
