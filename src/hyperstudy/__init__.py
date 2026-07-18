"""HyperStudy Python SDK — access experiment data from notebooks and scripts.

Usage::

    import hyperstudy

    hs = hyperstudy.HyperStudy(api_key="hst_live_...")
    events = hs.get_events("experiment_id")

Building experiments programmatically::

    from hyperstudy import HyperStudy, Experiment, State, show_text

    exp = Experiment(
        name="Welcome study",
        states=[State(id="s1", focus_component=show_text("Hello"))],
    )
    hs = HyperStudy(api_key="hst_live_...")
    info = hs.create_experiment(experiment=exp)
"""

from ._types import DataType, RatingKind, Scope
from .client import HyperStudy
from .exceptions import (
    AuthenticationError,
    ForbiddenError,
    HyperStudyError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from .models import (
    AgentConfig,
    ComponentType,
    DisconnectTimeout,
    Experiment,
    FocusComponent,
    GlobalComponentType,
    Guardrails,
    InstructionsPage,
    Persona,
    PostExperimentQuestionnaire,
    PromptLayer,
    Role,
    State,
    TransitionRules,
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

__version__ = "0.5.0"

__all__ = [
    "HyperStudy",
    "__version__",
    # Exceptions
    "HyperStudyError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
    # Enums
    "Scope",
    "DataType",
    "RatingKind",
    "ComponentType",
    "GlobalComponentType",
    # Experiment builders
    "Experiment",
    "State",
    "FocusComponent",
    "Role",
    "AgentConfig",
    "PromptLayer",
    "Persona",
    "Guardrails",
    "TransitionRules",
    "WaitingRoomConfig",
    "DisconnectTimeout",
    "InstructionsPage",
    "PostExperimentQuestionnaire",
    # Component factories
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
