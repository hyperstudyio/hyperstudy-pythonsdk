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


def test_factory_generates_id_when_omitted():
    a = show_text("a")
    b = show_text("b")
    assert a.id and b.id and a.id != b.id


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
