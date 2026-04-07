"""Main HyperStudy client — the primary entry point for the SDK."""

from __future__ import annotations

from typing import Any

from ._dataframe import to_pandas, to_polars
from ._http import HttpTransport
from ._pagination import fetch_all_pages
from ._types import Scope
from .experiments import ExperimentMixin


class HyperStudy(ExperimentMixin):
    """Client for the HyperStudy API v3.

    Args:
        api_key: Your API key (``hst_live_...`` or ``hst_test_...``).
            Also reads the ``HYPERSTUDY_API_KEY`` environment variable.
        base_url: API base URL. Defaults to the production endpoint.
        timeout: Request timeout in seconds.

    Example::

        import hyperstudy

        hs = hyperstudy.HyperStudy(api_key="hst_live_...")
        events = hs.get_events("experiment_id")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.hyperstudy.io/api/v3",
        timeout: int = 30,
    ):
        self._transport = HttpTransport(
            api_key=api_key, base_url=base_url, timeout=timeout
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Check API connectivity and version."""
        return self._transport.get("health")

    # ------------------------------------------------------------------
    # Data retrieval — one method per data type
    # ------------------------------------------------------------------

    def get_events(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        category: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch experiment events.

        Args:
            scope_id: ID of the experiment, room, or participant.
            scope: ``"experiment"``, ``"room"``, or ``"participant"``.
            room_id: Required when ``scope="participant"``.
            start_time: ISO 8601 start filter.
            end_time: ISO 8601 end filter.
            category: Event category filter.
            sort: Sort field (e.g. ``"onset"``, ``"timestamp"``).
            order: ``"asc"`` or ``"desc"``.
            limit: Max records. ``None`` fetches all pages.
            offset: Starting offset.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
            progress: Show progress bar when paginating.
        """
        return self._fetch_data(
            "events", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            category=category, sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_recordings(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch video/audio recording metadata."""
        return self._fetch_data(
            "recordings", scope_id,
            scope=scope, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_chat(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch text chat messages."""
        return self._fetch_data(
            "chat", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_videochat(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch LiveKit video chat connection data."""
        return self._fetch_data(
            "videochat", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_sync(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        aggregation_window: int | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch media synchronization metrics."""
        extra: dict[str, Any] = {}
        if aggregation_window is not None:
            extra["aggregationWindow"] = aggregation_window
        return self._fetch_data(
            "sync", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
            **extra,
        )

    def get_ratings(
        self,
        scope_id: str,
        *,
        kind: str = "continuous",
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch rating data.

        Args:
            kind: ``"continuous"`` (slider) or ``"sparse"`` (button-press).
            *: All other args are the same as :meth:`get_events`.
        """
        return self._fetch_data(
            f"ratings/{kind}", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_components(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch component response data."""
        return self._fetch_data(
            "components", scope_id,
            scope=scope, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_participants(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch participant data."""
        return self._fetch_data(
            "participants", scope_id,
            scope=scope, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_rooms(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch room/session data."""
        return self._fetch_data(
            "rooms", scope_id,
            scope=scope,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    # ------------------------------------------------------------------
    # Convenience: category-filtered events
    # ------------------------------------------------------------------

    def get_questionnaire(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch questionnaire responses.

        Convenience wrapper around :meth:`get_events` with
        ``category="questionnaire"``.
        """
        return self._fetch_data(
            "events", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            category="questionnaire", sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_instructions(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch instruction / comprehension-check events.

        Fetches ``pre_experiment`` events and filters to those whose
        ``eventType`` starts with ``"instructions."``.
        """
        return self._fetch_and_filter(
            "instructions.", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_consent(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch consent events.

        Fetches ``pre_experiment`` events and filters to those whose
        ``eventType`` starts with ``"consent."``.
        """
        return self._fetch_and_filter(
            "consent.", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    # ------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------

    def list_deployments(
        self,
        *,
        experiment_id: str | None = None,
        status: str | None = None,
        output: str = "pandas",
    ):
        """List deployments for the authenticated user.

        Args:
            experiment_id: Filter by experiment.
            status: Filter by deployment status.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
        """
        params: dict[str, Any] = {}
        if experiment_id:
            params["experimentId"] = experiment_id
        if status:
            params["status"] = status

        body = self._transport.get("deployments", params=params or None)
        data = body.get("data", [])
        return self._convert_output(data, output)

    def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        """Get deployment details.

        Returns:
            Deployment dict.
        """
        body = self._transport.get(f"deployments/{deployment_id}")
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data

    def get_deployment_sessions(
        self,
        deployment_id: str,
        *,
        output: str = "pandas",
    ):
        """List rooms/sessions for a deployment.

        Args:
            deployment_id: Deployment ID.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
        """
        body = self._transport.get(f"deployments/{deployment_id}/sessions")
        data = body.get("data", [])
        return self._convert_output(data, output)

    # ------------------------------------------------------------------
    # Convenience: all data for a participant
    # ------------------------------------------------------------------

    def get_all_data(
        self,
        participant_id: str,
        *,
        room_id: str,
        output: str = "pandas",
    ) -> dict:
        """Fetch all data types for one participant in a room.

        Returns:
            Dict mapping data type names to DataFrames (or dicts).
        """
        common = dict(scope="participant", room_id=room_id, output=output, progress=False)
        return {
            "events": self.get_events(participant_id, **common),
            "recordings": self.get_recordings(participant_id, **common),
            "chat": self.get_chat(participant_id, **common),
            "videochat": self.get_videochat(participant_id, **common),
            "sync": self.get_sync(participant_id, **common),
            "ratings_continuous": self.get_ratings(participant_id, kind="continuous", **common),
            "ratings_sparse": self.get_ratings(participant_id, kind="sparse", **common),
            "components": self.get_components(participant_id, **common),
            "questionnaire": self.get_questionnaire(participant_id, **common),
            "instructions": self.get_instructions(participant_id, **common),
            "consent": self.get_consent(participant_id, **common),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_and_filter(
        self,
        event_type_prefix: str,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch pre_experiment events and filter by eventType prefix.

        Used by :meth:`get_instructions` and :meth:`get_consent` which
        share the ``pre_experiment`` category but need client-side
        filtering on the ``eventType`` field.
        """
        # Always fetch as dicts so we can filter before conversion
        raw = self._fetch_data(
            "events", scope_id,
            scope=scope, room_id=room_id,
            start_time=start_time, end_time=end_time,
            category="pre_experiment", sort=sort, order=order,
            limit=limit, offset=offset,
            output="dict", progress=progress,
        )
        filtered = [
            e for e in raw
            if e.get("eventType", "").startswith(event_type_prefix)
        ]
        return self._convert_output(filtered, output)

    def _fetch_data(
        self,
        data_type: str,
        scope_id: str,
        *,
        scope: str = "experiment",
        room_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        category: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
        **extra_params,
    ):
        """Generic data-fetching logic shared by all ``get_*`` methods."""
        scope_val = Scope(scope)
        path = f"data/{data_type}/{scope_val.value}/{scope_id}"

        params: dict[str, Any] = {"offset": offset}
        if room_id:
            params["roomId"] = room_id
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if category:
            params["category"] = category
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        params.update(extra_params)

        # Single page or all pages
        if limit is not None:
            params["limit"] = limit
            body = self._transport.get(path, params=params)
            data = body.get("data", [])
        else:
            data, _ = fetch_all_pages(
                self._transport, path, params=params, progress=progress
            )

        return self._convert_output(data, output)

    @staticmethod
    def _convert_output(data: list[dict], output: str):
        """Convert raw dicts to the requested output format."""
        if output == "dict":
            return data
        if output == "polars":
            return to_polars(data)
        # Default: pandas
        return to_pandas(data)
