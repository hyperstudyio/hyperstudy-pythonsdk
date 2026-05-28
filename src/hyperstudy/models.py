"""Typed builders for HyperStudy experiment definitions.

Mirrors the JSON schema at ``shared/schemas/experiment.schema.json`` in the
main repo. The outer shape (Experiment / State / FocusComponent / Role) is
typed; per-component ``config`` payloads are validated server-side and remain
``dict[str, Any]`` here on purpose. Unknown top-level fields are preserved
via ``extra="allow"`` so the SDK does not block on backend additions.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class ComponentType(str, Enum):
    """Focus component types (one per state)."""

    SHOW_TEXT = "showtext"
    SHOW_IMAGE = "showimage"
    SHOW_VIDEO = "showvideo"
    VAS_RATING = "vasrating"
    TEXT_INPUT = "textinput"
    MULTIPLE_CHOICE = "multiplechoice"
    WAITING = "waiting"
    CODE = "code"
    CONTINUOUS_RATING = "continuousrating"
    VIDEO_CHAT = "videochat"
    TEXT_CHAT = "textchat"
    RAPID_RATE = "rapidrate"
    AUDIO_RECORDING = "audiorecording"
    SPARSE_RATING = "sparserating"
    TRIGGER = "trigger"
    RANKING = "ranking"
    SCANNER_PULSE_RECORDER = "scannerpulserecorder"
    LIKERT_SCALE = "likertscale"
    GAZE_OVERLAY = "gazeoverlay"


class GlobalComponentType(str, Enum):
    """Component types that may run as global (persistent) components."""

    CONTINUOUS_RATING = "continuousrating"
    VIDEO_CHAT = "videochat"
    TEXT_CHAT = "textchat"
    SPARSE_RATING = "sparserating"
    SCANNER_PULSE_RECORDER = "scannerpulserecorder"
    GAZE_OVERLAY = "gazeoverlay"


_BASE_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="allow",
    use_enum_values=True,
)


class _Model(BaseModel):
    model_config = _BASE_CONFIG


class FocusComponent(_Model):
    """Primary component displayed in a single state.

    ``config`` is component-type-specific and validated by the backend's
    ``componentSchemaValidator``. Use the factory helpers in this module
    (``show_text``, ``vas_rating``, ...) for ergonomic construction.
    """

    type: ComponentType
    config: dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class TransitionRules(_Model):
    """Rules governing how the experiment transitions from a state."""

    type: Optional[str] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)


class State(_Model):
    """An experiment state — a single screen/phase."""

    id: str
    name: Optional[str] = None
    order: Optional[int] = Field(default=None, ge=0)
    focus_component: Optional[FocusComponent] = None
    transition_rules: Optional[TransitionRules] = None
    global_components_visibility: Optional[dict[str, bool]] = None


class Role(_Model):
    """Participant role definition for multi-participant experiments."""

    name: Optional[str] = None
    participant_count: Optional[int] = Field(default=None, ge=0)


class WaitingRoomConfig(_Model):
    max_wait_time_ms: Optional[int] = Field(default=None, ge=0)
    countdown_time_ms: Optional[int] = Field(default=None, ge=0)


class DisconnectTimeout(_Model):
    enabled: Optional[bool] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)
    auto_reconnect_delay: Optional[int] = Field(default=None, ge=0)


class InstructionsPage(_Model):
    title: Optional[str] = None
    content: Optional[str] = None


class PostExperimentQuestionnaire(_Model):
    enabled: Optional[bool] = None
    questions: Optional[list[dict[str, Any]]] = None


class Experiment(_Model):
    """Root experiment definition. Only ``name`` is required.

    Use ``.model_dump(by_alias=True, exclude_none=True)`` to produce a
    wire-ready payload, or pass directly to ``client.create_experiment(
    experiment=exp)``.
    """

    name: str = Field(min_length=1)
    description: Optional[str] = None
    required_participants: Optional[int] = Field(default=None, ge=1)
    randomize_states: Optional[bool] = None
    states: Optional[list[State]] = None
    roles: Optional[dict[str, Role]] = None
    global_components: Optional[dict[str, dict[str, Any]]] = None
    variables: Optional[dict[str, Any]] = None
    waiting_room_config: Optional[WaitingRoomConfig] = None
    disconnect_timeout: Optional[DisconnectTimeout] = None
    completion_screen_duration_ms: Optional[int] = Field(default=None, ge=0)
    consent_form_enabled: Optional[bool] = None
    consent_form_title: Optional[str] = None
    consent_form_content: Optional[str] = None
    instructions_enabled: Optional[bool] = None
    instructions_title: Optional[str] = None
    instructions_content: Optional[str] = None
    instructions_pages: Optional[list[InstructionsPage]] = None
    post_experiment_questionnaire: Optional[PostExperimentQuestionnaire] = None


# ---------------------------------------------------------------------------
# Component factory helpers
# ---------------------------------------------------------------------------
#
# Each factory builds a ``FocusComponent`` with the standard config keys for
# its component type. Extra config keys pass through via ``**extra`` so users
# can set any field the backend accepts without needing a new factory.


def show_text(text: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showtext`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_TEXT,
        config={"text": text, **extra},
        id=id or _new_id(),
    )


def show_image(url: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showimage`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_IMAGE,
        config={"url": url, **extra},
        id=id or _new_id(),
    )


def show_video(url: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showvideo`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_VIDEO,
        config={"url": url, **extra},
        id=id or _new_id(),
    )


def vas_rating(
    prompt: str,
    *,
    output_variable: str,
    id: Optional[str] = None,
    **extra: Any,
) -> FocusComponent:
    """Build a ``vasrating`` (visual analog scale) focus component."""
    return FocusComponent(
        type=ComponentType.VAS_RATING,
        config={"prompt": prompt, "outputVariable": output_variable, **extra},
        id=id or _new_id(),
    )


def text_input(
    prompt: str,
    *,
    output_variable: str,
    id: Optional[str] = None,
    **extra: Any,
) -> FocusComponent:
    """Build a ``textinput`` focus component."""
    return FocusComponent(
        type=ComponentType.TEXT_INPUT,
        config={"prompt": prompt, "outputVariable": output_variable, **extra},
        id=id or _new_id(),
    )


def multiple_choice(
    prompt: str,
    options: list[str],
    *,
    output_variable: str,
    id: Optional[str] = None,
    **extra: Any,
) -> FocusComponent:
    """Build a ``multiplechoice`` focus component."""
    return FocusComponent(
        type=ComponentType.MULTIPLE_CHOICE,
        config={
            "prompt": prompt,
            "options": list(options),
            "outputVariable": output_variable,
            **extra,
        },
        id=id or _new_id(),
    )


def waiting(duration_ms: int, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``waiting`` focus component."""
    return FocusComponent(
        type=ComponentType.WAITING,
        config={"durationMs": int(duration_ms), **extra},
        id=id or _new_id(),
    )


def likert_scale(
    prompt: str,
    *,
    output_variable: str,
    scale_points: int = 7,
    id: Optional[str] = None,
    **extra: Any,
) -> FocusComponent:
    """Build a ``likertscale`` focus component."""
    return FocusComponent(
        type=ComponentType.LIKERT_SCALE,
        config={
            "prompt": prompt,
            "outputVariable": output_variable,
            "scalePoints": int(scale_points),
            **extra,
        },
        id=id or _new_id(),
    )


def ranking(
    prompt: str,
    options: list[str],
    *,
    output_variable: str,
    id: Optional[str] = None,
    **extra: Any,
) -> FocusComponent:
    """Build a ``ranking`` focus component."""
    return FocusComponent(
        type=ComponentType.RANKING,
        config={
            "prompt": prompt,
            "options": list(options),
            "outputVariable": output_variable,
            **extra,
        },
        id=id or _new_id(),
    )


__all__ = [
    # Enums
    "ComponentType",
    "GlobalComponentType",
    # Models
    "Experiment",
    "State",
    "FocusComponent",
    "TransitionRules",
    "Role",
    "WaitingRoomConfig",
    "DisconnectTimeout",
    "InstructionsPage",
    "PostExperimentQuestionnaire",
    # Factories
    "show_text",
    "show_image",
    "show_video",
    "vas_rating",
    "text_input",
    "multiple_choice",
    "waiting",
    "likert_scale",
    "ranking",
]
