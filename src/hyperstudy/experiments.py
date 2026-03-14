"""Experiment CRUD methods (mixed into HyperStudy via inheritance)."""

from __future__ import annotations

from typing import Any

from ._display import ExperimentInfo
from ._http import HttpTransport
from ._pagination import fetch_all_pages


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

    def create_experiment(self, *, name: str, **kwargs) -> ExperimentInfo:
        """Create a new experiment.

        Args:
            name: Experiment name (required).
            **kwargs: Additional fields (config, states, roles, description, etc.).

        Returns:
            The created :class:`ExperimentInfo`.
        """
        payload = {"name": name, **kwargs}
        body = self._transport.post("experiments", json=payload)
        data = body.get("data", [])
        record = data[0] if isinstance(data, list) and data else data
        return ExperimentInfo(record)

    def update_experiment(self, experiment_id: str, **kwargs) -> dict[str, Any]:
        """Update an experiment.

        Args:
            experiment_id: ID of the experiment to update.
            **kwargs: Fields to update (name, config, states, etc.).

        Returns:
            Update confirmation dict.
        """
        body = self._transport.put(f"experiments/{experiment_id}", json=kwargs)
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
