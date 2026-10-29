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

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


# Fields whose IMMEDIATE child keys are user-defined names (variable names, role
# names, component ids), NOT schema fields — their keys must NOT be camelCased.
# Their values are still recursed into.
_FREEFORM_MAP_FIELDS = frozenset({
    "variables", "roles", "globalComponents", "globalComponentsVisibility",
    "roleOverrides",
})

# Fields whose whole value goes on the wire exactly as written, as
# (parent field, field) pairs; a parent of None is the top level of an
# experiment or persona payload. Their keys belong to someone else: a
# provider's raw request params (extraParams), the voice engine's
# turn-detection settings, which use OpenAI's snake_case names
# (engineTurnDetection), and names the researcher chose (cognition contexts,
# stimulus mappings, free-form metadata). Matching on position, not the bare
# key, keeps a variable or role that happens to be named "metadata" a variable.
_VERBATIM_FIELDS = frozenset({
    (None, "extraParams"), (None, "cognition"), (None, "stimulusMappings"),
    (None, "metadata"), (None, "prolific_config"),
    ("voiceTurnTaking", "engineTurnDetection"),
})

# Experiment fields the backend stores under snake_case names.
_SNAKE_CASE_FIELDS = frozenset({"prolific_enabled", "prolific_config"})


def _wire_key(key: str) -> str:
    return key if key in _SNAKE_CASE_FIELDS else to_camel(key)


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True, exclude_none=True)


def camelize_wire(value: Any, _parent_key: "str | None" = None) -> Any:
    """Recursively convert snake_case dict keys to camelCase for the wire format.

    Skips converting the immediate keys of free-form map fields (variables, roles,
    globalComponents, globalComponentsVisibility) — those are user-defined names —
    but still recurses into their values. Values of ``_VERBATIM_FIELDS`` are
    passed through untouched; their positions are relative to the payload root,
    so call this on a whole experiment or persona payload, not a sub-dict.

    A typed model is dumped in its own wire format, the same one the typed
    builders send: its declared fields are aliased and its dict-valued fields
    are sent as written.
    """
    if isinstance(value, BaseModel):
        return _dump(value)
    if isinstance(value, dict):
        skip_keys = _parent_key in _FREEFORM_MAP_FIELDS
        out: dict[str, Any] = {}
        for k, v in value.items():
            new_key = k if skip_keys else (_wire_key(k) if isinstance(k, str) else k)
            if (_parent_key, new_key) in _VERBATIM_FIELDS:
                out[new_key] = _dump(v) if isinstance(v, BaseModel) else v
            else:
                out[new_key] = camelize_wire(v, _parent_key=new_key)
        return out
    if isinstance(value, list):
        return [camelize_wire(v, _parent_key=_parent_key) for v in value]
    return value


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
    id: str = Field(default_factory=_new_id)

    @field_validator("id", mode="before")
    @classmethod
    def _default_id(cls, v: "str | None") -> str:
        return v or _new_id()


class TransitionRules(_Model):
    """Rules governing how the experiment transitions from a state."""

    type: Optional[str] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)


class State(_Model):
    """An experiment state — a single screen/phase."""

    id: str = Field(min_length=1)
    name: Optional[str] = None
    order: Optional[int] = Field(default=None, ge=0)
    focus_component: Optional[FocusComponent] = None
    transition_rules: Optional[TransitionRules] = None
    global_components_visibility: Optional[dict[str, bool]] = None


class Role(_Model):
    """Participant role definition for multi-participant experiments.

    Set ``mode="agent"`` and ``persona_id`` to have an AI agent (persona
    from your library) fill this role instead of a human participant.
    """

    name: Optional[str] = None
    participant_count: Optional[int] = Field(default=None, ge=0)
    mode: Optional[str] = None  # "human" (default) or "agent"
    persona_id: Optional[str] = None


class PromptLayer(_Model):
    """Structured prompt fields, used for per-role agent overrides.

    Overrides are APPENDED to the bound persona's own prompt fields —
    they never replace the persona's identity.
    """

    persona: Optional[str] = None
    objective: Optional[str] = None
    guidance: Optional[str] = None
    examples: Optional[list[str]] = None
    additional_instructions: Optional[str] = None


class EngineTurnDetection(BaseModel):
    """Turn detection handed to the voice engine.

    The keys are the engine's own (OpenAI realtime) names, so unlike every
    other model here this one is sent in snake_case, exactly as written.
    ``server_vad`` takes ``threshold``, ``prefix_padding_ms`` and
    ``silence_duration_ms``; ``semantic_vad`` takes ``eagerness``.
    """

    model_config = ConfigDict(extra="allow")

    type: str  # "server_vad" | "semantic_vad"
    threshold: Optional[float] = Field(default=None, ge=0, le=1)
    prefix_padding_ms: Optional[int] = Field(default=None, ge=0, le=2000)
    silence_duration_ms: Optional[int] = Field(default=None, ge=100, le=5000)
    eagerness: Optional[str] = None  # semantic_vad: low | medium | high | auto


class VoiceTurnTaking(_Model):
    """How an experiment's voice agents take turns.

    Unset, the engine detects turns with ``server_vad`` and 500 ms of
    silence, and a spoken reply is cut off after 60 s.
    """

    mode: Optional[str] = None  # "engine" (the only mode so far)
    engine_turn_detection: Optional[EngineTurnDetection] = None
    min_response_delay_ms: Optional[int] = Field(default=None, ge=0, le=10_000)
    max_response_ms: Optional[int] = Field(default=None, ge=1000, le=300_000)


class VoiceTranscription(_Model):
    """Transcription of participants' speech by the voice engine (off unless enabled).

    ``language`` is a two-letter ISO-639-1 hint for a study run in one
    language; unset, the model detects it.
    """

    enabled: Optional[bool] = None
    model: Optional[str] = None  # gpt-4o-transcribe (default) | gpt-4o-mini-transcribe | whisper-1
    language: Optional[str] = Field(default=None, pattern=r"^[a-z]{2}$")


class AgentConfig(_Model):
    """Experiment-level agent inputs.

    The bound persona is the source of truth for provider/model/prompt and
    voice; the experiment contributes per-role prompt overrides, pacing, the
    random seed, and how its voice agents take turns and transcribe speech.
    """

    role_overrides: Optional[dict[str, PromptLayer]] = None
    pacing: Optional[dict[str, Any]] = None  # sent as written: {"readingOffsetMs": 300, ...}
    seed: Optional[int] = None
    voice_turn_taking: Optional[VoiceTurnTaking] = None
    voice_transcription: Optional[VoiceTranscription] = None


class Guardrails(_Model):
    """Per-agent safety limits. Unset fields use platform defaults
    (100 turns / 500k tokens); budgets fail closed when exceeded."""

    max_turns: Optional[int] = Field(default=None, ge=1)
    budget_tokens: Optional[int] = Field(default=None, ge=1000)
    budget_usd: Optional[float] = Field(default=None, gt=0)
    max_consecutive_decision_errors: Optional[int] = Field(default=None, ge=1)


class RealtimeVoice(_Model):
    """The realtime speech engine behind a voice persona."""

    provider: str  # "openai" (the only provider so far)
    model: Optional[str] = None  # e.g. "gpt-realtime-2.1"; the provider's default when unset


class PersonaVoice(_Model):
    """Gives a persona a voice in the experiment's audio.

    Only ``engine="realtime"`` with ``realtime=RealtimeVoice(provider="openai")``
    is supported so far. ``preset`` is the provider's voice (OpenAI: alloy,
    ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar); ``style``
    is natural-language delivery direction, e.g. ``"warm, a little hesitant"``.
    """

    engine: str  # "realtime"
    preset: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0.25, le=1.5)
    style: Optional[str] = Field(default=None, max_length=500)
    realtime: Optional[RealtimeVoice] = None


class PersonaChat(_Model):
    """Whether the agent opens a text chat, and how long it waits first."""

    initiate: Optional[bool] = None
    initiate_delay_ms: Optional[int] = Field(default=None, gt=0)


class Persona(_Model):
    """A reusable AI-agent definition (agent library entry).

    The persona owns the agent's identity, model settings, guardrails,
    voice and (optionally) cognition. ``cognition`` is accepted as a plain
    dict — its schema is experimental and still evolving. Offline loops live
    inside ``cognition["config"]["contexts"][<name>]["offline"]``.

    ``display_name`` is the name other participants see in chat and video;
    empty, they see ``name``.
    """

    name: str = Field(min_length=1)
    display_name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[PromptLayer] = None
    provider: Optional[str] = None  # anthropic (default) | openai | gemini | custom
    model: Optional[str] = None  # required when provider == "custom"
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    thinking: Optional[bool] = None
    reasoning_effort: Optional[str] = None
    extra_params: Optional[dict[str, Any]] = None
    disable_thinking: Optional[bool] = None
    seed: Optional[int] = None
    cognition: Optional[dict[str, Any]] = None
    memory_persistence: Optional[str] = None  # "none" (default) | "cross-experiment"
    seed_memories: Optional[list[dict[str, Any]]] = None
    guardrails: Optional[Guardrails] = None
    pacing: Optional[dict[str, Any]] = None  # sent as written: {"readingOffsetMs": 300, ...}
    chat: Optional[PersonaChat] = None
    voice: Optional[PersonaVoice] = None
    visibility: Optional[str] = None  # private (default) | organization | public


class WaitingRoomConfig(_Model):
    max_wait_time_ms: Optional[int] = Field(default=None, ge=0)
    countdown_time_ms: Optional[int] = Field(default=None, ge=0)


class DisconnectTimeout(_Model):
    enabled: Optional[bool] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)
    auto_reconnect_delay: Optional[int] = Field(default=None, ge=0)


class ExperimenterMessageStyle(_Model):
    """Text style of messages the experimenter sends from deployment monitoring.

    Unset, messages are 20px white.
    """

    font_size: Optional[float] = Field(default=None, ge=10, le=72)
    color: Optional[str] = Field(default=None, pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


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
    runtime: Optional[str] = None  # "v2" required for agent-only deployments
    agent_config: Optional[AgentConfig] = None
    randomize_states: Optional[bool] = None
    states: Optional[list[State]] = None
    roles: Optional[dict[str, Role]] = None
    global_components: Optional[dict[GlobalComponentType, dict[str, Any]]] = None
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
    # Only the owner or an organization admin may change visibility.
    visibility: Optional[str] = None  # private (default) | organization | public
    tags: Optional[list[str]] = None
    enable_participant_messaging: Optional[bool] = None
    experimenter_message_style: Optional[ExperimenterMessageStyle] = None
    stimulus_mappings: Optional[dict[str, Any]] = None
    device_integration: Optional[dict[str, Any]] = None
    # Stored under snake_case names by the backend.
    prolific_enabled: Optional[bool] = Field(default=None, alias="prolific_enabled")
    prolific_config: Optional[dict[str, Any]] = Field(default=None, alias="prolific_config")


# ---------------------------------------------------------------------------
# Component factory helpers
# ---------------------------------------------------------------------------
#
# Each factory builds a ``FocusComponent`` with the standard config keys for
# its component type. Extra config keys pass through via ``**extra`` so users
# can set any field the backend accepts without needing a new factory.


# Across all factories, ``**extra`` is spread FIRST so factory-set config
# keys win on collision. A user who accidentally passes the camelCase
# version of a documented snake_case arg (e.g. ``outputVariable=`` instead
# of ``output_variable=``) gets the factory's value, not their typo.


def _config_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """A factory's extra kwargs, converted as fields of a component ``config``."""
    return camelize_wire(extra, _parent_key="config")


def show_text(text: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showtext`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_TEXT,
        config={**_config_extra(extra), "text": text},
        id=id,
    )


def show_image(url: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showimage`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_IMAGE,
        config={**_config_extra(extra), "url": url},
        id=id,
    )


def show_video(url: str, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``showvideo`` focus component."""
    return FocusComponent(
        type=ComponentType.SHOW_VIDEO,
        config={**_config_extra(extra), "url": url},
        id=id,
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
        config={**_config_extra(extra), "prompt": prompt, "outputVariable": output_variable},
        id=id,
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
        config={**_config_extra(extra), "prompt": prompt, "outputVariable": output_variable},
        id=id,
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
            **_config_extra(extra),
            "prompt": prompt,
            "options": list(options),
            "outputVariable": output_variable,
        },
        id=id,
    )


def waiting(duration_ms: int, *, id: Optional[str] = None, **extra: Any) -> FocusComponent:
    """Build a ``waiting`` focus component."""
    return FocusComponent(
        type=ComponentType.WAITING,
        config={**_config_extra(extra), "durationMs": int(duration_ms)},
        id=id,
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
            **_config_extra(extra),
            "prompt": prompt,
            "outputVariable": output_variable,
            "scalePoints": int(scale_points),
        },
        id=id,
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
            **_config_extra(extra),
            "prompt": prompt,
            "options": list(options),
            "outputVariable": output_variable,
        },
        id=id,
    )


__all__ = [
    # Enums
    "ComponentType",
    "GlobalComponentType",
    # Wire conversion helper
    "camelize_wire",
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
    "ExperimenterMessageStyle",
    # Agent models
    "AgentConfig",
    "PromptLayer",
    "VoiceTurnTaking",
    "EngineTurnDetection",
    "VoiceTranscription",
    "Persona",
    "PersonaVoice",
    "RealtimeVoice",
    "PersonaChat",
    "Guardrails",
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
