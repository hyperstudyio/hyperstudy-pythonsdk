"""Tests for the typed experiment builders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hyperstudy import (
    ComponentType,
    Experiment,
    FocusComponent,
    GlobalComponentType,
    Role,
    State,
    WaitingRoomConfig,
    likert_scale,
    multiple_choice,
    ranking,
    show_image,
    show_text,
    show_video,
    text_input,
    vas_rating,
    waiting,
)

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA_PATH = FIXTURES / "experiment.schema.json"


# ---------------------------------------------------------------------------
# Round-trip & alias coverage
# ---------------------------------------------------------------------------


def test_minimal_experiment_round_trip():
    """An experiment with only required fields serializes to the expected wire shape."""
    exp = Experiment(name="My Study")
    assert exp.model_dump(by_alias=True, exclude_none=True) == {"name": "My Study"}


def test_snake_case_serializes_to_camel_case():
    """Snake_case Python fields produce camelCase wire keys."""
    exp = Experiment(
        name="X",
        required_participants=2,
        randomize_states=True,
        completion_screen_duration_ms=5000,
    )
    wire = exp.model_dump(by_alias=True, exclude_none=True)
    assert wire == {
        "name": "X",
        "requiredParticipants": 2,
        "randomizeStates": True,
        "completionScreenDurationMs": 5000,
    }


def test_camel_case_input_also_accepted():
    """Wire-shape input (camelCase) works thanks to populate_by_name."""
    exp = Experiment.model_validate({"name": "Y", "requiredParticipants": 3})
    assert exp.required_participants == 3


def test_full_experiment_round_trip():
    """A multi-state, multi-role experiment round-trips through dump."""
    exp = Experiment(
        name="Two-person study",
        description="Speaker / listener task",
        required_participants=2,
        states=[
            State(
                id="welcome",
                name="Welcome",
                order=0,
                focus_component=show_text("Welcome", id="ft_welcome"),
            ),
            State(
                id="rate",
                order=1,
                focus_component=vas_rating(
                    "How do you feel?",
                    output_variable="mood",
                    id="ft_rate",
                ),
            ),
        ],
        roles={
            "speaker": Role(name="Speaker", participant_count=1),
            "listener": Role(name="Listener", participant_count=1),
        },
        waiting_room_config=WaitingRoomConfig(
            max_wait_time_ms=60000,
            countdown_time_ms=3000,
        ),
    )
    wire = exp.model_dump(by_alias=True, exclude_none=True)

    assert wire["name"] == "Two-person study"
    assert wire["requiredParticipants"] == 2
    assert wire["waitingRoomConfig"] == {
        "maxWaitTimeMs": 60000,
        "countdownTimeMs": 3000,
    }
    assert wire["states"][0] == {
        "id": "welcome",
        "name": "Welcome",
        "order": 0,
        "focusComponent": {
            "type": "showtext",
            "config": {"text": "Welcome"},
            "id": "ft_welcome",
        },
    }
    assert wire["states"][1]["focusComponent"]["type"] == "vasrating"
    assert wire["states"][1]["focusComponent"]["config"]["outputVariable"] == "mood"
    assert wire["roles"] == {
        "speaker": {"name": "Speaker", "participantCount": 1},
        "listener": {"name": "Listener", "participantCount": 1},
    }


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_name_is_required():
    with pytest.raises(ValidationError):
        Experiment()  # type: ignore[call-arg]


def test_name_must_be_non_empty():
    with pytest.raises(ValidationError):
        Experiment(name="")


def test_required_participants_must_be_positive():
    with pytest.raises(ValidationError):
        Experiment(name="X", required_participants=0)


def test_invalid_component_type_rejected():
    with pytest.raises(ValidationError):
        FocusComponent(type="not_a_component", config={})  # type: ignore[arg-type]


def test_state_id_required():
    with pytest.raises(ValidationError):
        State()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# extra="allow" — forward compatibility with backend additions
# ---------------------------------------------------------------------------


def test_unknown_top_level_field_preserved():
    """Backend can ship a new top-level field before the SDK adds typed support."""
    exp = Experiment.model_validate({"name": "X", "futureFeatureFlag": True})
    wire = exp.model_dump(by_alias=True, exclude_none=True)
    assert wire["futureFeatureFlag"] is True


def test_real_backend_response_round_trips():
    """Parsing an actual backend response shape preserves all extras.

    Backend responses include many server-populated audit fields
    (`ownerId`, `createdAt`, `roomCount`, etc.) that the SDK's typed
    shape does not declare. `extra="allow"` must accept them on
    validate and emit them on dump, so a round-trip
    ``Experiment.model_validate(...).model_dump(...)`` is lossless.
    """
    fixture = json.loads(
        (FIXTURES / "experiment_single_response.json").read_text()
    )
    raw = fixture["data"][0]
    exp = Experiment.model_validate(raw)
    wire = exp.model_dump(by_alias=True, exclude_none=True)
    # Every key in the original should round-trip.
    for key, value in raw.items():
        assert wire[key] == value, f"field {key!r} did not round-trip"


# ---------------------------------------------------------------------------
# Component factories
# ---------------------------------------------------------------------------


def test_show_text_factory():
    c = show_text("Hello", id="x")
    assert c.type == ComponentType.SHOW_TEXT.value
    assert c.config == {"text": "Hello"}
    assert c.id == "x"


def test_show_image_factory():
    c = show_image("https://example.com/a.png", id="x")
    assert c.type == ComponentType.SHOW_IMAGE.value
    assert c.config == {"url": "https://example.com/a.png"}


def test_show_video_factory():
    c = show_video("https://example.com/a.mp4", id="x")
    assert c.type == ComponentType.SHOW_VIDEO.value
    assert c.config == {"url": "https://example.com/a.mp4"}


def test_vas_rating_factory():
    c = vas_rating("How happy?", output_variable="happy", id="x")
    assert c.type == ComponentType.VAS_RATING.value
    assert c.config == {"prompt": "How happy?", "outputVariable": "happy"}


def test_text_input_factory():
    c = text_input("Your name?", output_variable="name", id="x")
    assert c.type == ComponentType.TEXT_INPUT.value
    assert c.config == {"prompt": "Your name?", "outputVariable": "name"}


def test_multiple_choice_factory():
    c = multiple_choice("Pick one", ["A", "B"], output_variable="pick", id="x")
    assert c.type == ComponentType.MULTIPLE_CHOICE.value
    assert c.config == {
        "prompt": "Pick one",
        "options": ["A", "B"],
        "outputVariable": "pick",
    }


def test_waiting_factory():
    c = waiting(3000, id="x")
    assert c.type == ComponentType.WAITING.value
    assert c.config == {"durationMs": 3000}


def test_likert_scale_factory_default_points():
    c = likert_scale("Agree?", output_variable="agree", id="x")
    assert c.type == ComponentType.LIKERT_SCALE.value
    assert c.config["scalePoints"] == 7


def test_ranking_factory():
    c = ranking("Rank these", ["X", "Y"], output_variable="order", id="x")
    assert c.type == ComponentType.RANKING.value
    assert c.config["options"] == ["X", "Y"]


def test_factory_passes_through_extra_config():
    """Extra kwargs land in the config dict so users can set any backend field."""
    c = show_text("Hi", id="x", fontSize=24, color="red")
    assert c.config == {"text": "Hi", "fontSize": 24, "color": "red"}


def test_factory_keys_win_over_extras_on_collision():
    """If an extra collides with a factory-set config key, the factory wins.

    Protects against a user passing the camelCase wire form of a
    documented snake_case arg (e.g. `outputVariable=...` instead of
    `output_variable=...`) and silently overwriting the real value.
    Note: collisions where the Python arg name and config key are
    identical (e.g. `show_text(text=...)`) are blocked by Python's
    own parameter binding — TypeError fires before the factory runs.
    """
    c = vas_rating(
        "How happy?",
        output_variable="real_value",
        outputVariable="bogus_override",
    )
    assert c.config["outputVariable"] == "real_value"

    c2 = waiting(3000, durationMs=9999)
    assert c2.config["durationMs"] == 3000


def test_factory_generates_id_when_omitted():
    a = show_text("a")
    b = show_text("b")
    assert a.id and b.id and a.id != b.id


# ---------------------------------------------------------------------------
# Fix A2 — factory **extra camelization
# ---------------------------------------------------------------------------


def test_factory_extra_snake_case_camelized():
    """Extra kwargs to factories are camelized so they land correctly on the wire."""
    c = show_text("hi", max_width=600)
    assert "maxWidth" in c.config
    assert c.config["maxWidth"] == 600
    assert "max_width" not in c.config


def test_vas_rating_factory_extra_camelized():
    """vas_rating extra kwargs with snake_case are camelized."""
    c = vas_rating("p", output_variable="ov", min_label="Low")
    assert "minLabel" in c.config
    assert c.config["minLabel"] == "Low"
    assert "outputVariable" in c.config
    assert "outputVariable" in c.config


# ---------------------------------------------------------------------------
# Fix E — schema enforcement on State.id and global_components
# ---------------------------------------------------------------------------


def test_state_id_empty_rejected():
    """State.id must be non-empty (minLength:1)."""
    with pytest.raises(ValidationError):
        State(id="")


def test_global_components_invalid_type_rejected():
    """global_components keys must be GlobalComponentType values."""
    with pytest.raises(ValidationError):
        Experiment(name="x", global_components={"showvideo": {}})


def test_global_components_valid_type_accepted():
    """Valid GlobalComponentType keys are accepted."""
    exp = Experiment(name="x", global_components={"videochat": {"option": 1}})
    wire = exp.model_dump(by_alias=True, exclude_none=True)
    assert wire["globalComponents"] == {"videochat": {"option": 1}}


def test_global_components_dumps_string_keys():
    """global_components keys must serialize as strings, not enum reprs."""
    exp = Experiment(name="x", global_components={"textchat": {}})
    wire = exp.model_dump(by_alias=True, exclude_none=True)
    keys = list(wire["globalComponents"].keys())
    assert keys == ["textchat"], f"Expected string keys but got: {keys}"


# ---------------------------------------------------------------------------
# Fix F — centralized FocusComponent id via before-validator
# ---------------------------------------------------------------------------


def test_focus_component_direct_construction_gets_id():
    """FocusComponent(type=..., config=...) gets an auto-generated id."""
    fc = FocusComponent(type=ComponentType.SHOW_TEXT, config={})
    assert fc.id is not None
    assert len(fc.id) == 8


def test_show_text_id_auto_generated():
    """show_text() without id= gets a non-empty id."""
    fc = show_text("hi")
    assert fc.id and len(fc.id) == 8


def test_show_text_explicit_id_preserved():
    """show_text(id='x') keeps the explicit id."""
    fc = show_text("hi", id="x")
    assert fc.id == "x"


# ---------------------------------------------------------------------------
# Schema-drift guard
# ---------------------------------------------------------------------------
#
# The schema vendored at tests/fixtures/experiment.schema.json is the source
# of truth for the experiment definition shape. When the backend schema
# changes (new component types, new required fields), the vendored copy
# should be refreshed AND this test will flag any drift in the models.
#
# Source: /Users/lukechang/Github/hyperstudy/shared/schemas/experiment.schema.json


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_focus_component_type_enum_matches_schema():
    """Symmetric check: schema enum and ComponentType must agree exactly."""
    schema = _load_schema()
    schema_enum = set(
        schema["properties"]["states"]["items"]["properties"]["focusComponent"][
            "properties"
        ]["type"]["enum"]
    )
    model_enum = {ct.value for ct in ComponentType}
    assert schema_enum == model_enum, (
        f"ComponentType drift: only-in-schema={schema_enum - model_enum}, "
        f"only-in-model={model_enum - schema_enum}"
    )


def test_global_component_type_enum_matches_schema():
    schema = _load_schema()
    schema_enum = set(
        schema["properties"]["globalComponents"]["propertyNames"]["enum"]
    )
    model_enum = {gct.value for gct in GlobalComponentType}
    assert schema_enum == model_enum, (
        f"GlobalComponentType drift: only-in-schema={schema_enum - model_enum}, "
        f"only-in-model={model_enum - schema_enum}"
    )


def test_experiment_required_fields_match_schema():
    """Schema-required fields must be both declared AND required on the model."""
    schema = _load_schema()
    required = set(schema.get("required", []))
    aliases_by_name = {
        name: (f.alias or name) for name, f in Experiment.model_fields.items()
    }
    declared = set(Experiment.model_fields.keys()) | set(aliases_by_name.values())
    missing = required - declared
    assert not missing, f"Experiment is missing schema-required fields: {missing}"

    # And: each schema-required field must be required on the model (no default).
    name_to_field = {
        (f.alias or name): f for name, f in Experiment.model_fields.items()
    }
    for req in required:
        field = name_to_field.get(req)
        assert field is not None, f"required schema field {req!r} not on model"
        assert field.is_required(), (
            f"schema requires {req!r} but model marks it optional"
        )


# ------------------------------------------------------------------
# Agent-role authoring (mode/persona_id, AgentConfig, runtime)
# ------------------------------------------------------------------


def test_agent_role_wire_format():
    """Agent-mode roles serialize mode and personaId in camelCase."""
    from hyperstudy import Role

    role = Role(name="Confederate", participant_count=1, mode="agent",
                persona_id="persona_abc")
    wire = role.model_dump(by_alias=True, exclude_none=True)

    assert wire == {
        "name": "Confederate",
        "participantCount": 1,
        "mode": "agent",
        "personaId": "persona_abc",
    }


def test_agent_config_wire_format_preserves_role_names():
    """agentConfig serializes with camelCase fields but role-name keys intact."""
    from hyperstudy import AgentConfig, Experiment, PromptLayer, Role

    exp = Experiment(
        name="Agent study",
        runtime="v2",
        roles={
            "my_speaker": Role(mode="agent", persona_id="persona_abc"),
        },
        agent_config=AgentConfig(
            role_overrides={
                "my_speaker": PromptLayer(
                    objective="Convince your partner.",
                    additional_instructions="Stay in character.",
                ),
            },
            pacing={"minDelayMs": 1500},
            seed=42,
        ),
    )
    wire = exp.model_dump(by_alias=True, exclude_none=True)

    assert wire["runtime"] == "v2"
    # Free-form role-name keys must survive untouched (not camelized)
    assert "my_speaker" in wire["roles"]
    assert wire["roles"]["my_speaker"]["personaId"] == "persona_abc"
    overrides = wire["agentConfig"]["roleOverrides"]
    assert "my_speaker" in overrides
    assert overrides["my_speaker"]["objective"] == "Convince your partner."
    assert overrides["my_speaker"]["additionalInstructions"] == "Stay in character."
    assert wire["agentConfig"]["seed"] == 42
