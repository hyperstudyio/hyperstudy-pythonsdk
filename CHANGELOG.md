# Changelog

## v0.4.1

### Breaking Changes

- **Removed `Persona.offline_cognition`.** The server now hard-discards this field (`offlineCognition` is always null server-side); offline loops live inside `cognition.config.contexts.<name>.offline`. The SDK also strips `offlineCognition` from create/update payloads so personas rebuilt from older API responses never send it.

### Features

- **Eye-tracking data access**: `get_eyetracking(scope_id, scope="experiment"|"room"|"participant", room_id=)` with the standard pagination/output options, plus `DataType.EYETRACKING`. `get_all_data` now includes an `eyetracking` key.
- **Room variables**: `get_variables(room_id)` — the reconstructed shared-variable timeline for a room. Returns `{writes, timeline, variable_names, dropped_writes}`: the write log (each write tagged with source and persisted flag), the per-state forward-filled snapshot matrix, the ordered variable set, and any writes that failed the server's ground-truth cross-checks (a bug signal).
- **Participant counts**: `get_counts(participant_id, room_id=)` — cheap per-data-type document counts (`counts` / `hasData`) for a participant in a room.
- **Experiment export**: `export_experiment(experiment_id)` — portable experiment JSON (definition plus media-asset manifest), suitable for re-import.
- **Cognition catalog**: `get_cognition_catalog()` — the valid building blocks for persona `cognition` configs (`abilities`, `recipes`, `offlineRecipes`). Requires the `read:personas` scope.

## v0.4.0

### Features

- **Agent data access**: new methods for AI-agent experiment data —
  `get_agent_decisions(scope_id, scope="experiment"|"room", detail=, limit=, participant_id=)` (per-turn decision logs plus run-manifest rows), `get_agent_decision(room_id, decision_id)` (single decision with full detail blobs: prompt, reasoning chain, peer-model snapshot, prediction update), and `get_agent_runs(experiment_id)` (run manifests with orphaned-run flags). Emits a warning when the server truncates decisions at the per-room limit.
- `DataType.AGENT_DECISIONS` and `DataType.AGENT_RUNS` enum entries; `get_all_data` now includes an `agent_decisions` key (room-scope fetch filtered to the participant).
- **Agent-role experiment authoring**: `Role` accepts `mode="agent"` and `persona_id`; new `AgentConfig` (per-role `role_overrides`, `pacing`, `seed`) and `PromptLayer` models; `Experiment` gains `runtime` and `agent_config` fields. Role-name keys in `role_overrides` are preserved (not camelized) on the wire.
- **Persona management**: `list_personas`, `get_persona`, `create_persona`, `update_persona` (merge-patch), `delete_persona`, `duplicate_persona`, with typed `Persona` / `Guardrails` builders. Requires API-key scopes `read:personas` / `write:personas`.
- **Agent deployment launch & control**: `create_deployment` (including agent-only deployments — rooms launch server-side immediately), `get_agent_spend`, `run_more`, `stop_room`, `retry_room`. Requires the `write:deployments` scope.

### Fixes

- `__version__` now matches the packaged version (was stuck at 0.3.0 while pyproject said 0.3.1).

## v0.3.1

### Features

- `download_recording` / `download_recordings` now mint a signed download URL via the recordings download endpoint (using each recording's `downloadPath`) and fall back to the legacy `downloadUrl`/`url` for older GCS-only recordings. Fixes downloads failing after the backend list endpoint stopped embedding signed URLs.

### Fixes

- Snake_case→camelCase conversion is now recursive for the raw-dict and `**kwargs` paths: nested keys (e.g. `waiting_room_config={"max_wait_time_ms": 5000}` → `{"waitingRoomConfig": {"maxWaitTimeMs": 5000}}`) and factory `**extra` kwargs are converted. Free-form map fields (`variables`, `roles`, `globalComponents`, `globalComponentsVisibility`) preserve their user-defined keys while still converting nested schema fields. Previously nested/extra snake_case keys were silently dropped on the wire.
- Downloads are now atomic: each file streams to `<dest>.part` and is renamed on success, so a mid-stream failure never destroys a pre-existing complete file. `skip_existing` again skips when `fileSize` is unknown (an existing file is necessarily complete).
- `update_experiment()` with no fields now raises `ValueError` instead of issuing an empty PUT.
- `State.id` enforces `min_length=1`; `Experiment.global_components` keys are validated against `GlobalComponentType` (rejected at construction, still serialized as strings on the wire).
- `FocusComponent.id` is auto-generated when omitted, including direct construction without a factory helper.


## v0.3.0

### Features

- Typed experiment builders for programmatic authoring. New top-level exports: `Experiment`, `State`, `FocusComponent`, `Role`, `WaitingRoomConfig`, `DisconnectTimeout`, `InstructionsPage`, `PostExperimentQuestionnaire`, `TransitionRules`, `ComponentType`, `GlobalComponentType`. Snake_case Python fields are converted to the camelCase wire format automatically; unknown top-level fields are preserved via `extra="allow"` so the SDK doesn't block on backend schema additions.
- Component factory helpers: `show_text`, `show_image`, `show_video`, `vas_rating`, `text_input`, `multiple_choice`, `waiting`, `likert_scale`, `ranking`. Extra kwargs pass through to the component `config` for any backend-supported field.
- `create_experiment` and `update_experiment` now accept an `experiment=Experiment(...)` argument alongside the existing `**kwargs` form. When both are given, kwargs override builder fields.
- New `validate_experiment(experiment)` method — dry-run against `POST /experiments/validate`.
- Schema-drift guard test: vendored copy of `experiment.schema.json` is checked against `ComponentType` / `GlobalComponentType` / required-field declarations so backend additions surface in CI.

### Backwards Compatibility

- `create_experiment(name=..., **kwargs)` continues to work unchanged.
- `update_experiment(experiment_id, **kwargs)` continues to work unchanged.

### Dependencies

- Adds `pydantic>=2.5`.

## v0.2.0

### Features

- Convenience methods for common event categories: `get_questionnaire`, `get_instructions`, `get_consent`
- Deployment management: `list_deployments`, `get_deployment`, `get_deployment_sessions`
- API warning surfacing: backend `_warnings` metadata now emitted via Python's `warnings` module
- `get_all_data` now includes `ratings_sparse`, `questionnaire`, `instructions`, and `consent`

### Breaking Changes

- `get_all_data` return keys changed: `"ratings"` split into `"ratings_continuous"` and `"ratings_sparse"`

## v0.1.0

Initial release.

### Features

- `HyperStudy` client with API key authentication (constructor arg or `HYPERSTUDY_API_KEY` env var)
- Data retrieval methods: `get_events`, `get_recordings`, `get_chat`, `get_videochat`, `get_sync`, `get_ratings`, `get_components`, `get_participants`, `get_rooms`
- `get_all_data` convenience method for fetching all data types for a single participant
- Auto-pagination with `tqdm` progress bars (notebook and terminal)
- Output format options: `"pandas"` (default), `"polars"`, `"dict"`
- Experiment management: `list_experiments`, `get_experiment`, `get_experiment_config`, `create_experiment`, `update_experiment`, `delete_experiment`
- Rich notebook display (`_repr_html_`) for experiment objects
- Typed exceptions: `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `ValidationError`, `ServerError`
- `health()` method for connection testing
