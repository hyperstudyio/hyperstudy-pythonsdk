"""Experiment CRUD methods (mixed into HyperStudy via inheritance)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from ._display import ExperimentInfo
from ._http import HttpTransport
from ._pagination import fetch_all_pages
from .models import camelize_wire

if TYPE_CHECKING:
    from .models import Experiment


def _build_experiment_payload(
    experiment: "Experiment | dict[str, Any] | None" = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Build a wire-ready dict from an Experiment instance or raw dict.

    - ``Experiment`` → ``.model_dump(by_alias=True, exclude_none=True)``
    - ``dict`` → shallow copy
    - ``None`` → empty dict

    ``overrides`` are merged on top (caller wins). Snake_case keys in
    overrides are translated to camelCase so they actually override the
    aliased fields of the dumped ``Experiment`` (otherwise a kwarg like
    ``required_participants=5`` would leave the builder's
    ``requiredParticipants`` in place and ALSO add ``required_participants``
    to the wire payload — both keys would go).
    """
    if experiment is None:
        payload: dict[str, Any] = {}
    elif isinstance(experiment, BaseModel):
        payload = experiment.model_dump(by_alias=True, exclude_none=True)
    elif isinstance(experiment, dict):
        payload = camelize_wire(experiment)
    else:
        raise TypeError(
            f"experiment must be an Experiment or dict, got {type(experiment).__name__}"
        )
    for key, value in overrides.items():
        ck = to_camel(key)
        payload[ck] = camelize_wire(value, _parent_key=ck)
    return payload


class ExperimentMixin:
    """Methods for experiment management. Mixed into the main client."""

    _transport: HttpTransport

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_experiments(
        self,
        *,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """List experiments accessible to the authenticated user.

        Args:
            search: Filter experiments by name/description substring.
            limit: Max experiments to return. ``None`` fetches all pages.
            offset: Starting offset for pagination.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
            progress: Show progress bar when paginating.

        Returns:
            DataFrame or list of dicts depending on *output*.
        """
        params: dict[str, Any] = {"offset": offset}
        if search:
            params["search"] = search

        if limit is not None:
            params["limit"] = limit
            body = self._transport.get("experiments", params=params)
            data = body.get("data", [])
        else:
            data, _ = fetch_all_pages(
                self._transport,
                "experiments",
                params=params,
                page_size=50,
                progress=progress,
            )

        return self._convert_output(data, output)

    def get_experiment(self, experiment_id: str) -> ExperimentInfo:
        """Get a single experiment with enriched metadata.

        Returns:
            An :class:`ExperimentInfo` object (dict-like, with ``_repr_html_``).
        """
        body = self._transport.get(f"experiments/{experiment_id}")
        data = body.get("data", [])
        record = data[0] if isinstance(data, list) and data else data
        return ExperimentInfo(record)

    def get_experiment_config(self, experiment_id: str) -> dict[str, Any]:
        """Get raw experiment config (lightweight, no enrichment)."""
        body = self._transport.get(f"experiments/{experiment_id}/config")
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        *,
        experiment: "Experiment | None" = None,
        name: str | None = None,
        **kwargs,
    ) -> ExperimentInfo:
        """Create a new experiment.

        Two equivalent ways to call this:

        - **Typed builder** (recommended): pass an :class:`Experiment` instance
          via the ``experiment`` argument. Snake_case fields on the model are
          converted to the camelCase wire format automatically. Fields added
          via ``extra="allow"`` (unknown to the SDK's typed shape) and entries
          in the per-component ``config`` dict pass through *verbatim* — use
          camelCase keys for those.
        - **Raw kwargs**: pass ``name=`` (required) and any additional fields
          as keyword arguments. Backwards-compatible with hyperstudy <= 0.2.x.

        When both forms are mixed, keyword arguments override fields from
        ``experiment`` — useful for ad-hoc overrides.

        Args:
            experiment: Typed experiment definition.
            name: Experiment name (required when ``experiment`` is omitted).
            **kwargs: Additional fields, or overrides applied on top of
                ``experiment``.

        Returns:
            The created :class:`ExperimentInfo`.
        """
        if name is not None:
            kwargs["name"] = name
        payload = _build_experiment_payload(experiment, **kwargs)
        if not payload.get("name"):
            raise TypeError(
                "create_experiment requires a 'name' "
                "(pass name=... or experiment=Experiment(name=...))"
            )
        body = self._transport.post("experiments", json=payload)
        data = body.get("data", [])
        record = data[0] if isinstance(data, list) and data else data
        return ExperimentInfo(record)

    def update_experiment(
        self,
        experiment_id: str,
        *,
        experiment: "Experiment | None" = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Update an experiment.

        Args:
            experiment_id: ID of the experiment to update.
            experiment: Optional typed :class:`Experiment` carrying the new
                fields. Snake_case → camelCase conversion is applied.
            **kwargs: Fields to update, or overrides applied on top of
                ``experiment``.

        Returns:
            Update confirmation dict.
        """
        payload = _build_experiment_payload(experiment, **kwargs)
        if not payload:
            raise ValueError(
                "update_experiment requires at least one field to update "
                "(pass experiment=... or keyword fields)."
            )
        body = self._transport.put(f"experiments/{experiment_id}", json=payload)
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data

    def validate_experiment(
        self,
        experiment: "Experiment | dict[str, Any]",
    ) -> dict[str, Any]:
        """Dry-run validation of an experiment definition against the backend.

        Returns the ``ValidationResultResponse`` body — typically
        ``{"valid": True}`` on success, or ``{"valid": False, "errors": [...]}``
        with a list of issues.

        Args:
            experiment: An :class:`Experiment` or a raw config dict.
        """
        if experiment is None:
            raise TypeError("validate_experiment requires an Experiment or dict")
        payload = _build_experiment_payload(experiment)
        body = self._transport.post("experiments/validate", json=payload)
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data

    def delete_experiment(
        self, experiment_id: str, *, skip_data_check: bool = False
    ) -> None:
        """Delete (soft-delete) an experiment.

        Args:
            experiment_id: ID of the experiment to delete.
            skip_data_check: If True, skip the confirmation check for experiments
                with collected data.
        """
        params = {}
        if skip_data_check:
            params["skipDataCheck"] = "true"
        self._transport.delete(f"experiments/{experiment_id}", params=params)
