"""Persona and experiment fields for voice agents, as they reach the wire."""

from __future__ import annotations

import json

import pydantic
import pytest
import responses

from hyperstudy import (
    AgentConfig,
    EngineTurnDetection,
    Experiment,
    ExperimenterMessageStyle,
    HyperStudy,
    Persona,
    PersonaChat,
    PersonaVoice,
    RealtimeVoice,
    VoiceTranscription,
    VoiceTurnTaking,
)

from .conftest import BASE_URL, envelope


def _sent(call_index: int = 0) -> dict:
    return json.loads(responses.calls[call_index].request.body)


VOICE_PERSONA_DOC = {
    "id": "persona-v",
    "name": "Interviewer",
    "displayName": "Sam",
    "provider": "openai",
    "voice": {
        "engine": "realtime",
        "preset": "marin",
        "speed": 1.1,
        "style": "warm, a little hesitant",
        "realtime": {"provider": "openai", "model": "gpt-realtime-2.1"},
    },
    "chat": {"initiate": True, "initiateDelayMs": 1500},
}


@responses.activate
def test_create_voice_persona_typed_builder(api_key):
    responses.post(f"{BASE_URL}/personas", json=envelope(VOICE_PERSONA_DOC), status=201)
    persona = Persona(
        name="Interviewer",
        display_name="Sam",
        provider="openai",
        voice=PersonaVoice(
            engine="realtime",
            preset="marin",
            speed=1.1,
            style="warm, a little hesitant",
            realtime=RealtimeVoice(provider="openai", model="gpt-realtime-2.1"),
        ),
        chat=PersonaChat(initiate=True, initiate_delay_ms=1500),
    )
    created = HyperStudy(api_key=api_key).create_persona(persona=persona)

    assert created["id"] == "persona-v"
    sent = _sent()
    assert sent["displayName"] == "Sam"
    assert sent["voice"] == VOICE_PERSONA_DOC["voice"]
    assert sent["chat"] == {"initiate": True, "initiateDelayMs": 1500}
    assert "display_name" not in sent


def test_persona_round_trips_from_api_response():
    """A persona read from the API rebuilds into a typed Persona and dumps back the same fields."""
    persona = Persona(**VOICE_PERSONA_DOC)
    assert persona.display_name == "Sam"
    assert persona.voice.realtime.model == "gpt-realtime-2.1"
    dumped = persona.model_dump(by_alias=True, exclude_none=True)
    for key in ("displayName", "voice", "chat"):
        assert dumped[key] == VOICE_PERSONA_DOC[key]


@pytest.mark.parametrize("bad", [{"speed": 2.0}, {"speed": 0.1}, {"style": "x" * 501}])
def test_persona_voice_rejects_out_of_range_values(bad):
    with pytest.raises(pydantic.ValidationError):
        PersonaVoice(engine="realtime", **bad)


@responses.activate
def test_persona_language_is_not_sent_and_warns(api_key):
    responses.post(f"{BASE_URL}/personas", json=envelope({"id": "p1"}), status=201)
    with pytest.warns(UserWarning, match="voice_transcription.language"):
        HyperStudy(api_key=api_key).create_persona(name="Old", language="en")
    assert "language" not in _sent()


@responses.activate
def test_update_persona_from_stored_doc_drops_language(api_key):
    """Older stored personas still carry `language`; rebuilding one must not resend it."""
    responses.put(f"{BASE_URL}/personas/p1", json=envelope({"id": "p1"}), status=200)
    stored = {"id": "p1", "name": "Old", "language": "en"}
    with pytest.warns(UserWarning):
        HyperStudy(api_key=api_key).update_persona("p1", persona=Persona(**stored))
    assert "language" not in _sent()


@responses.activate
def test_experiment_voice_agent_config_typed_builder(api_key):
    responses.post(f"{BASE_URL}/experiments", json=envelope({"id": "exp-1", "name": "Voice"}), status=201)
    experiment = Experiment(
        name="Voice",
        runtime="v2",
        agent_config=AgentConfig(
            voice_turn_taking=VoiceTurnTaking(
                mode="engine",
                engine_turn_detection=EngineTurnDetection(
                    type="server_vad", threshold=0.6, prefix_padding_ms=300, silence_duration_ms=800
                ),
                min_response_delay_ms=250,
                max_response_ms=30_000,
            ),
            voice_transcription=VoiceTranscription(enabled=True, model="gpt-4o-transcribe", language="en"),
        ),
    )
    HyperStudy(api_key=api_key).create_experiment(experiment=experiment)

    agent_config = _sent()["agentConfig"]
    assert agent_config["voiceTurnTaking"] == {
        "mode": "engine",
        # The engine's own keys stay snake_case.
        "engineTurnDetection": {
            "type": "server_vad", "threshold": 0.6, "prefix_padding_ms": 300, "silence_duration_ms": 800,
        },
        "minResponseDelayMs": 250,
        "maxResponseMs": 30_000,
    }
    assert agent_config["voiceTranscription"] == {"enabled": True, "model": "gpt-4o-transcribe", "language": "en"}


def test_voice_settings_reject_out_of_range_values():
    with pytest.raises(pydantic.ValidationError):
        EngineTurnDetection(type="server_vad", silence_duration_ms=50)
    with pytest.raises(pydantic.ValidationError):
        VoiceTurnTaking(max_response_ms=500)
    with pytest.raises(pydantic.ValidationError):
        VoiceTranscription(language="english")


@responses.activate
def test_experiment_new_top_level_fields(api_key):
    responses.post(f"{BASE_URL}/experiments", json=envelope({"id": "exp-1", "name": "Study"}), status=201)
    experiment = Experiment(
        name="Study",
        visibility="organization",
        tags=["pilot"],
        enable_participant_messaging=True,
        experimenter_message_style=ExperimenterMessageStyle(font_size=28, color="#ffcc00"),
        stimulus_mappings={"face_set_a": {"happy_face": "a.png"}},
        prolific_enabled=True,
    )
    HyperStudy(api_key=api_key).create_experiment(experiment=experiment)

    sent = _sent()
    assert sent["visibility"] == "organization"
    assert sent["tags"] == ["pilot"]
    assert sent["enableParticipantMessaging"] is True
    assert sent["experimenterMessageStyle"] == {"fontSize": 28, "color": "#ffcc00"}
    assert sent["stimulusMappings"] == {"face_set_a": {"happy_face": "a.png"}}
    assert sent["prolific_enabled"] is True
