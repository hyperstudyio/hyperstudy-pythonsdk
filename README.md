# hyperstudy

Python SDK for the [HyperStudy](https://hyperstudy.io) experiment platform API. Designed for researchers working in Jupyter, marimo, or Python scripts.

## Installation

```bash
pip install hyperstudy
```

For polars support:

```bash
pip install hyperstudy[polars]
```

## Quick Start

```python
import hyperstudy

hs = hyperstudy.HyperStudy(api_key="hst_live_...")
# Or set the HYPERSTUDY_API_KEY environment variable

# Fetch events as a pandas DataFrame
events = hs.get_events("your_experiment_id")

# Room-scoped data
events = hs.get_events("room_id", scope="room")

# Participant-scoped data
events = hs.get_events("participant_id", scope="participant", room_id="room_id")
```

## Data Types

All data retrieval methods follow the same pattern:

```python
events        = hs.get_events("exp_id")
recordings    = hs.get_recordings("exp_id")
chat          = hs.get_chat("exp_id")
videochat     = hs.get_videochat("exp_id")
sync          = hs.get_sync("exp_id")
ratings       = hs.get_ratings("exp_id", kind="continuous")
eyetracking   = hs.get_eyetracking("exp_id")
components    = hs.get_components("exp_id")
participants  = hs.get_participants("exp_id")
rooms         = hs.get_rooms("exp_id")

# Convenience methods for common event categories
questionnaire = hs.get_questionnaire("exp_id")
instructions  = hs.get_instructions("exp_id")
consent       = hs.get_consent("exp_id")

# Room-scoped: reconstructed shared-variable timeline
# -> {"writes", "timeline", "variable_names", "dropped_writes"}
variables = hs.get_variables("room_id")

# Per-data-type document counts for one participant in a room
counts = hs.get_counts("participant_id", room_id="room_id")
```

### Output Formats

```python
df_pandas = hs.get_events("exp_id")                      # pandas (default)
df_polars = hs.get_events("exp_id", output="polars")     # polars
raw       = hs.get_events("exp_id", output="dict")       # list[dict]
```

### Filtering

```python
events = hs.get_events(
    "exp_id",
    start_time="2024-01-01T10:00:00Z",
    end_time="2024-01-01T12:00:00Z",
    category="component",
    sort="onset",
    limit=100,
)
```

### Auto-Pagination

When `limit` is not set, all pages are fetched automatically with a progress bar:

```python
all_events = hs.get_events("exp_id")  # fetches all pages
```

## Experiment Management

```python
# List experiments
experiments = hs.list_experiments()

# Get details (with rich display in notebooks)
exp = hs.get_experiment("exp_id")

# Quick create / update / delete (kwargs form, backwards-compatible)
new_exp = hs.create_experiment(name="My Study", description="...")
hs.update_experiment("exp_id", name="Updated Name")
hs.delete_experiment("exp_id")

# Portable experiment JSON (definition + media-asset manifest)
export = hs.export_experiment("exp_id")
```

### Building experiments programmatically (0.3.0+)

For full experiment definitions — states, components, roles — use the typed `Experiment` builder. Snake_case Python fields convert to the camelCase wire format automatically.

```python
from hyperstudy import Experiment, State, Role, show_text, vas_rating

exp = Experiment(
    name="Two-person study",
    required_participants=2,
    states=[
        State(id="intro", focus_component=show_text("Welcome")),
        State(
            id="rate",
            focus_component=vas_rating("Rate the clip", output_variable="rating"),
        ),
    ],
    roles={"speaker": Role(name="Speaker", participant_count=1)},
)

# Dry-run validation against the backend.
print(hs.validate_experiment(exp))  # → {"valid": True, ...}

# Create.
info = hs.create_experiment(experiment=exp)
```

Component factories cover `show_text`, `show_image`, `show_video`, `vas_rating`, `text_input`, `multiple_choice`, `waiting`, `likert_scale`, `ranking`. For other component types, construct directly: `FocusComponent(type=ComponentType.X, config={...})`. See the [Experiment Authoring guide](https://docs.hyperstudy.io/experimenters/api-access/experiment-authoring) for the full reference.

## Deployments

```python
# List deployments
deployments = hs.list_deployments()
deployments = hs.list_deployments(experiment_id="exp_id", status="active")

# Get deployment details
dep = hs.get_deployment("deployment_id")

# List sessions/rooms for a deployment
sessions = hs.get_deployment_sessions("deployment_id")
```

## AI Agents

Full agent workflow support: personas (the agent library), agent-role experiment authoring, agent-only deployment launch/control, and agent data.

```python
from hyperstudy import Persona, PromptLayer, Guardrails, Role, AgentConfig

# --- Personas (agent library) ---
persona = hs.create_persona(persona=Persona(
    name="Curious Undergrad",
    provider="anthropic",
    model="claude-opus-4-8",
    prompt=PromptLayer(persona="You are a curious undergraduate...",
                       objective="Converse naturally with your partner."),
    guardrails=Guardrails(max_turns=50, budget_usd=2.0),
))
personas = hs.list_personas()
hs.update_persona(persona["id"], description="Updated")  # merge-patch

# --- Agent roles in experiments ---
exp = hs.create_experiment(experiment=Experiment(
    name="Agent study",
    runtime="v2",  # required for agent-only deployments
    roles={"partner": Role(mode="agent", persona_id=persona["id"])},
    agent_config=AgentConfig(seed=42),
    states=[...],
))

# --- Agent-only deployment ---
dep = hs.create_deployment(exp["id"], config={
    "type": "agent-only",
    "agentDeployment": {"rooms": 10, "budgetUsd": 5.0},
})
spend = hs.get_agent_spend(dep["id"])           # live spend vs budget
hs.run_more(dep["id"], rooms=5, budget_usd=2.5) # additive batch

# --- Agent data ---
decisions = hs.get_agent_decisions(exp["id"])                    # per-turn logs
runs = hs.get_agent_runs(exp["id"])                              # run manifests
detail = hs.get_agent_decision("room_id", "participantId_3")     # full blobs

# --- Cognition authoring catalog ---
catalog = hs.get_cognition_catalog()  # {"abilities": ..., "recipes": ..., "offlineRecipes": ...}
```

Persona methods need the `read:personas` / `write:personas` API-key scopes; deployment launch/control needs `write:deployments`; agent data reads need `read:events`.

## All Data for a Participant

```python
data = hs.get_all_data("participant_id", room_id="room_id")
# Returns dict with keys: events, recordings, chat, videochat, sync,
# ratings_continuous, ratings_sparse, components, eyetracking,
# questionnaire, instructions, consent, agent_decisions
```

## API Key

Generate an API key from the HyperStudy dashboard under Settings. Keys follow the format `hst_{environment}_{key}` and are passed via the `X-API-Key` header.

## Documentation

Full documentation: [docs.hyperstudy.io/developers/python-sdk](https://docs.hyperstudy.io/developers/python-sdk)

## Development

```bash
git clone https://github.com/hyperstudyio/hyperstudy-pythonsdk.git
cd hyperstudy-pythonsdk
pip install -e ".[dev,polars]"
pytest --cov=hyperstudy
ruff check src/
```

## License

MIT
