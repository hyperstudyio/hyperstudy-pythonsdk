# Changelog

## v0.3.0

### Features

- Typed experiment builders for programmatic authoring. New top-level exports: `Experiment`, `State`, `FocusComponent`, `Role`, `WaitingRoomConfig`, `DisconnectTimeout`, `InstructionsPage`, `PostExperimentQuestionnaire`, `TransitionRules`, `ComponentType`, `GlobalComponentType`. Snake_case Python fields are converted to the camelCase wire format automatically; unknown top-level fields are preserved via `extra="allow"` so the SDK doesn't block on backend schema additions.
- Component factory helpers: `show_text`, `show_image`, `show_video`, `vas_rating`, `text_input`, `multiple_choice`, `waiting`, `likert_scale`, `ranking`. Extra kwargs pass through to the component `config` for any backend-supported field.
- `create_experiment` and `update_experiment` now accept an `experiment=Experiment(...)` argument alongside the existing `**kwargs` form. When both are given, kwargs override builder fields.
- New `validate_experiment(experiment)` method — dry-run against `POST /experiments/validate`.
- Schema-drift guard test: vendored copy of `experiment.schema.json` is checked against `ComponentType` / `GlobalComponentType` / required-field declarations so backend additions surface in CI.
- `download_recording` / `download_recordings` now mint a signed URL via `downloadPath` (auth'd endpoint returning a short-lived GCS URL); falls back to a legacy absolute `downloadUrl`/`url` for older recordings.

### Hardening

- Snake_case→camelCase conversion is now recursive: raw-dict experiments and override kwargs have their nested keys fully converted. Free-form map fields (`variables`, `roles`, `globalComponents`, `globalComponentsVisibility`) preserve their immediate keys (user-defined names) while still converting nested schema fields.
- Factory `**extra` kwargs are also recursively camelized (e.g. `show_text("hi", max_width=600)` produces `{"maxWidth": 600, "text": "hi"}`).
- Downloads are now atomic: the file streams to `<dest>.part` and is renamed on success, so a mid-stream failure leaves any pre-existing complete file at `dest` intact.
- `skip_existing` now skips when `fileSize` is unknown (previous behavior forced a re-download). Because downloads are atomic, any existing file is necessarily complete.
- `update_experiment()` with no fields raises `ValueError` instead of sending an empty PUT.
- `State.id` enforces `min_length=1` (mirrors the JSON schema's `minLength: 1`).
- `Experiment.global_components` keys are validated against `GlobalComponentType`; invalid component types are rejected at construction time. Keys serialize as strings on the wire.
- `FocusComponent.id` is auto-generated when not supplied (including direct construction without using a factory helper).

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
