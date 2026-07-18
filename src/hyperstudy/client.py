"""Main HyperStudy client — the primary entry point for the SDK."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from tqdm.auto import tqdm

from ._dataframe import to_pandas, to_polars
from ._downloads import build_filename, download_file, get_download_url
from ._http import HttpTransport
from ._pagination import fetch_all_pages
from ._types import Scope
from .exceptions import HyperStudyError
from .experiments import ExperimentMixin
from .personas import PersonaMixin


class HyperStudy(ExperimentMixin, PersonaMixin):
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
        deployment_id: str | None = None,
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
            deployment_id: Filter by deployment (experiment scope only).
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch video/audio recording metadata."""
        return self._fetch_data(
            "recordings", scope_id,
            scope=scope, deployment_id=deployment_id, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_chat(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
            start_time=start_time, end_time=end_time,
            sort=sort, order=order,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_eyetracking(
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
        """Fetch eye-tracking gaze data.

        Args:
            scope_id: ID of the experiment, room, or participant.
            scope: ``"experiment"``, ``"room"``, or ``"participant"``.
            room_id: Required when ``scope="participant"``.
            limit: Max records. ``None`` fetches all pages.
            offset: Starting offset.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
            progress: Show progress bar when paginating.
        """
        return self._fetch_data(
            "eyetracking", scope_id,
            scope=scope, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_components(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch component response data."""
        return self._fetch_data(
            "components", scope_id,
            scope=scope, deployment_id=deployment_id, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_participants(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
        room_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch participant data."""
        return self._fetch_data(
            "participants", scope_id,
            scope=scope, deployment_id=deployment_id, room_id=room_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_rooms(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        output: str = "pandas",
        progress: bool = True,
    ):
        """Fetch room/session data."""
        return self._fetch_data(
            "rooms", scope_id,
            scope=scope, deployment_id=deployment_id,
            limit=limit, offset=offset,
            output=output, progress=progress,
        )

    def get_variables(
        self,
        room_id: str,
        *,
        output: str = "pandas",
    ):
        """Fetch the reconstructed shared-variable timeline for a room.

        Returns a dict with four keys:

        - ``writes`` — the time-ordered write log (one row per variable
          write: seeded constant, human component response, or agent
          submit-response, tagged with source and persisted flag), converted
          per ``output``
        - ``timeline`` — the derived per-state forward-filled variable
          snapshot matrix, converted per ``output``
        - ``variable_names`` — ordered list of every variable seen
        - ``matrix_columns`` — ordered column set of the timeline matrix
        - ``dropped_writes`` — writes that failed the server's ground-truth
          cross-checks (a bug signal; empty is the healthy state)
        - ``mode`` — the reconstruction mode the server processor ran in

        Args:
            room_id: Room ID.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``
                for the tabular values.
        """
        body = self._transport.get(f"data/variables/room/{room_id}")
        metadata = body.get("metadata") or {}
        return {
            "writes": self._convert_output(body.get("data", []), output),
            "timeline": self._convert_output(metadata.get("timeline") or [], output),
            "variable_names": metadata.get("variableNames") or [],
            "matrix_columns": metadata.get("matrixColumns") or [],
            "dropped_writes": metadata.get("droppedWrites") or [],
            "mode": metadata.get("mode"),
        }

    def get_counts(
        self,
        participant_id: str,
        room_id: str,
    ) -> dict[str, Any]:
        """Fetch per-data-type document counts for a participant in a room.

        Cheap count queries grouped by data type — useful for checking
        which data types exist before fetching them.

        Args:
            participant_id: Participant ID.
            room_id: Room ID.

        Returns:
            Dict with ``counts`` and ``hasData`` keyed by data type.
        """
        body = self._transport.get(
            f"data/counts/participant/{participant_id}", params={"roomId": room_id}
        )
        data = body.get("data", [])
        return data[0] if isinstance(data, list) and data else data

    # ------------------------------------------------------------------
    # Convenience: category-filtered events
    # ------------------------------------------------------------------

    def get_questionnaire(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
    # Deployments — agent-deployment write surface
    # ------------------------------------------------------------------

    def create_deployment(
        self,
        experiment_id: str,
        *,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a deployment (requires the ``write:deployments`` scope).

        For an agent-only deployment, pass::

            hs.create_deployment(
                "exp_123",
                config={
                    "name": "Pilot batch",
                    "type": "agent-only",
                    "agentDeployment": {"rooms": 10, "budgetUsd": 5.0},
                },
            )

        Agent rooms launch server-side immediately after creation. Preflight
        failures (missing persona binding, missing provider key, unreachable
        custom endpoint) raise :class:`ValidationError` with per-role reasons.

        Args:
            experiment_id: The experiment to deploy (agent-only requires
                ``runtime="v2"`` and at least one agent-mode role).
            config: Deployment config dict (camelCase keys, as above).
            **kwargs: Extra config fields, merged into ``config``.

        Returns:
            The created deployment dict.
        """
        merged = {**(config or {}), **kwargs}
        body = self._transport.post(
            "deployments", json={"experimentId": experiment_id, "config": merged}
        )
        return body.get("data", {})

    def get_agent_spend(self, deployment_id: str) -> dict[str, Any]:
        """Total + per-room agent LLM spend for an agent-only deployment."""
        body = self._transport.get(f"deployments/{deployment_id}/agent-spend")
        return body.get("data", {})

    def run_more(
        self, deployment_id: str, *, rooms: int, budget_usd: float
    ) -> dict[str, Any]:
        """Launch additional agent rooms on an existing agent-only deployment.

        Args:
            deployment_id: The deployment to extend.
            rooms: Number of additional rooms.
            budget_usd: Additional budget for this batch (added to the
                deployment's cumulative budget cap).

        Returns:
            Dict with the launched ``batchId`` and ``requestedRooms``.
        """
        body = self._transport.post(
            f"deployments/{deployment_id}/run-more",
            json={"rooms": rooms, "budgetUsd": budget_usd},
        )
        return body.get("data", {})

    def stop_room(self, deployment_id: str, room_id: str) -> None:
        """Force-end a running agent room."""
        self._transport.post(f"deployments/{deployment_id}/rooms/{room_id}/stop")

    def retry_room(self, deployment_id: str, room_id: str) -> dict[str, Any]:
        """Re-spawn a fresh room for a spawn-failed one (reuses the budget pool)."""
        body = self._transport.post(
            f"deployments/{deployment_id}/rooms/{room_id}/retry"
        )
        return body.get("data", {})

    # ------------------------------------------------------------------
    # Agent data — decisions and run manifests
    # ------------------------------------------------------------------

    def get_agent_decisions(
        self,
        scope_id: str,
        *,
        scope: str = "experiment",
        detail: bool = False,
        limit: int | None = None,
        participant_id: str | None = None,
        output: str = "pandas",
    ):
        """Fetch AI-agent decision logs (and run manifests).

        Every agent turn is logged as a decision record; each agent's run
        also produces one manifest row. Room-scope responses tag rows with
        ``_type`` (``"decision"`` or ``"run"``).

        Args:
            scope_id: Experiment ID or room ID, depending on ``scope``.
            scope: ``"experiment"`` (default, all rooms) or ``"room"``.
            detail: Include full detail blobs (prompt, reasoning chain,
                peer-model snapshot, prediction update) on each decision row.
            limit: Max decisions per room (server default 5000). When the
                cap is hit a truncation warning is emitted.
            participant_id: Optionally filter rows to one agent participant
                (applied client-side).
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
        """
        if scope not in ("experiment", "room"):
            raise ValueError(f"scope must be 'experiment' or 'room', got {scope!r}")

        params: dict[str, Any] = {}
        if detail:
            params["detail"] = "true"
        if limit is not None:
            params["limit"] = limit

        body = self._transport.get(
            f"data/agent-decisions/{scope}/{scope_id}", params=params or None
        )
        data = body.get("data", [])
        if (body.get("metadata") or {}).get("truncated"):
            warnings.warn(
                "Agent decisions were truncated by the per-room limit; "
                "pass a higher limit= to fetch more.",
                stacklevel=2,
            )
        if participant_id is not None:
            data = [row for row in data if row.get("participantId") == participant_id]
        return self._convert_output(data, output)

    def get_agent_decision(
        self, room_id: str, decision_id: str
    ) -> dict[str, Any]:
        """Fetch one agent decision with full detail blobs.

        Args:
            room_id: Room the decision belongs to.
            decision_id: Decision document ID (``{participantId}_{seq}``).

        Returns:
            Decision dict including prompt, reasoning chain, peer-model
            snapshot, and prediction update.
        """
        body = self._transport.get(
            f"data/agent-decisions/room/{room_id}/decision/{decision_id}"
        )
        return body.get("data", {})

    def get_agent_runs(
        self,
        experiment_id: str,
        *,
        output: str = "pandas",
    ):
        """Fetch agent run manifests for an experiment.

        One row per agent run: model, provider, token/cost totals, seed,
        persona ID, and code version. Runs whose room ended abnormally are
        flagged as orphaned.

        Args:
            experiment_id: Experiment ID.
            output: ``"pandas"`` (default), ``"polars"``, or ``"dict"``.
        """
        body = self._transport.get(f"data/agent-runs/experiment/{experiment_id}")
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
            "eyetracking": self.get_eyetracking(participant_id, **common),
            "questionnaire": self.get_questionnaire(participant_id, **common),
            "instructions": self.get_instructions(participant_id, **common),
            "consent": self.get_consent(participant_id, **common),
            "agent_decisions": self.get_agent_decisions(
                room_id, scope="room", participant_id=participant_id, output=output
            ),
        }

    # ------------------------------------------------------------------
    # Recording downloads
    # ------------------------------------------------------------------

    def _download_url_for(self, recording: dict[str, Any]) -> str | None:
        """Resolve a directly-downloadable URL for a recording.

        Prefers the auth'd mint endpoint (``downloadPath`` -> short-lived signed GCS
        URL); falls back to a legacy absolute ``downloadUrl``/``url`` for old
        GCS-only recordings.
        """
        download_path = recording.get("downloadPath")
        if download_path:
            body = self._transport.get(download_path)
            return (body.get("data") or {}).get("url")
        return get_download_url(recording)

    def download_recording(
        self,
        recording: dict[str, Any],
        output_dir: str = ".",
    ) -> Path:
        """Download a single recording file to disk.

        Args:
            recording: A recording dict (from ``get_recordings(output="dict")``).
            output_dir: Directory to save the file.

        Returns:
            Path to the downloaded file.
        """
        url = self._download_url_for(recording)
        if not url:
            raise ValueError("Recording has no downloadUrl or url field")

        dest_dir = Path(output_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = build_filename(recording)
        dest = dest_dir / filename
        download_file(url, dest)
        return dest

    def download_recordings(
        self,
        scope_id: str,
        *,
        output_dir: str,
        scope: str = "experiment",
        deployment_id: str | None = None,
        room_id: str | None = None,
        recording_type: str | None = None,
        progress: bool = True,
        skip_existing: bool = True,
    ):
        """Download recording files to disk.

        Fetches recording metadata, downloads each file from its signed
        URL, writes a ``recordings_metadata.csv`` sidecar, and returns a
        DataFrame with a ``local_path`` column.

        Args:
            scope_id: Experiment, room, or participant ID.
            output_dir: Directory to save files.
            scope: ``"experiment"``, ``"room"``, or ``"participant"``.
            deployment_id: Filter by deployment (experiment scope only).
            room_id: Filter by room.
            recording_type: ``"audio"``, ``"video"``, or ``None`` (both).
            progress: Show progress bar.
            skip_existing: Skip files already on disk with matching size.

        Returns:
            pandas DataFrame with recording metadata plus ``local_path``
            and ``download_status`` columns.
        """
        try:
            # Signing per-recording GCS URLs scales with count; 30s default is too short.
            recordings = self._fetch_data(
                "recordings",
                scope_id,
                scope=scope,
                deployment_id=deployment_id,
                room_id=room_id,
                output="dict",
                timeout=300,
            )
        except Exception as exc:
            raise HyperStudyError(
                f"Failed to list recordings for {scope}={scope_id!r}: {exc}",
                code=getattr(exc, "code", "LIST_RECORDINGS_FAILED"),
                status_code=getattr(exc, "status_code", None),
                details=getattr(exc, "details", None),
            ) from exc

        if recording_type:
            recordings = [
                r for r in recordings
                if (r.get("metadata") or {}).get("type") == recording_type
            ]

        dest_dir = Path(output_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        local_paths: list[str | None] = []
        statuses: list[str] = []
        failed_count = 0

        for rec in tqdm(recordings, desc="Downloading recordings", disable=not progress):
            filename = build_filename(rec)
            dest = dest_dir / filename

            # Check skip before resolving the URL (avoids minting a signed URL unnecessarily).
            if skip_existing and dest.exists():
                expected_size = rec.get("fileSize")
                # dest is always a fully-written file (atomic rename), so skip when size is
                # unknown OR matches; only re-download on a definite size mismatch.
                if expected_size is None or dest.stat().st_size == expected_size:
                    local_paths.append(str(dest.resolve()))
                    statuses.append("skipped")
                    continue

            url = self._download_url_for(rec)
            if not url:
                local_paths.append(None)
                statuses.append("failed")
                failed_count += 1
                warnings.warn(f"Recording {rec.get('recordingId')} has no download URL")
                continue

            try:
                download_file(url, dest)
                local_paths.append(str(dest.resolve()))
                statuses.append("downloaded")
            except Exception as exc:
                local_paths.append(None)
                statuses.append("failed")
                failed_count += 1
                warnings.warn(
                    f"Failed to download recording {rec.get('recordingId')}: {exc}"
                )

        if failed_count:
            warnings.warn(
                f"{failed_count}/{len(recordings)} recordings failed to download; "
                "see the 'download_status' column for per-file results."
            )

        df = to_pandas(recordings)
        if not df.empty:
            df["local_path"] = local_paths
            df["download_status"] = statuses
            df.to_csv(dest_dir / "recordings_metadata.csv", index=False)

        return df

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_and_filter(
        self,
        event_type_prefix: str,
        scope_id: str,
        *,
        scope: str = "experiment",
        deployment_id: str | None = None,
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
            scope=scope, deployment_id=deployment_id, room_id=room_id,
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
        deployment_id: str | None = None,
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
        timeout: int | float | None = None,
        **extra_params,
    ):
        """Generic data-fetching logic shared by all ``get_*`` methods."""
        scope_val = Scope(scope)
        path = f"data/{data_type}/{scope_val.value}/{scope_id}"

        params: dict[str, Any] = {"offset": offset}
        if deployment_id:
            params["deploymentId"] = deployment_id
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
            body = self._transport.get(path, params=params, timeout=timeout)
            data = body.get("data", [])
        else:
            data, _ = fetch_all_pages(
                self._transport,
                path,
                params=params,
                progress=progress,
                timeout=timeout,
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
