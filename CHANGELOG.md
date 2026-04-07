# Changelog

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
