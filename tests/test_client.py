"""Tests for the main HyperStudy client data-retrieval methods."""

from __future__ import annotations

import os
import warnings

import pandas as pd
import pytest
import responses

from hyperstudy import HyperStudy
from hyperstudy.exceptions import AuthenticationError, ForbiddenError

BASE_URL = "https://api.hyperstudy.io/api/v3"


@pytest.fixture
def api_key():
    return "hst_test_abc123"


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------


def test_client_requires_api_key():
    """Client raises AuthenticationError when no key is provided."""
    env = os.environ.copy()
    env.pop("HYPERSTUDY_API_KEY", None)
    # Temporarily clear env var if set
    original = os.environ.pop("HYPERSTUDY_API_KEY", None)
    try:
        with pytest.raises(AuthenticationError, match="No API key"):
            HyperStudy()
    finally:
        if original is not None:
            os.environ["HYPERSTUDY_API_KEY"] = original


def test_client_reads_env_var(monkeypatch):
    """Client reads HYPERSTUDY_API_KEY from the environment."""
    monkeypatch.setenv("HYPERSTUDY_API_KEY", "hst_test_envkey")
    client = HyperStudy()
    assert client._transport._session.headers["X-API-Key"] == "hst_test_envkey"


# ------------------------------------------------------------------
# Data retrieval — get_events
# ------------------------------------------------------------------


@responses.activate
def test_get_events_pandas(api_key, events_response):
    """get_events returns a pandas DataFrame by default."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_events("exp_abc123", limit=1000)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "onset_sec" in df.columns
    assert df["onset_sec"].iloc[0] == pytest.approx(1.5)


@responses.activate
def test_get_events_dict(api_key, events_response):
    """get_events with output='dict' returns raw list of dicts."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    data = client.get_events("exp_abc123", output="dict", limit=1000)

    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["id"] == "evt_001"


@responses.activate
def test_get_events_room_scope(api_key, events_response):
    """get_events with scope='room' uses the correct URL path."""
    responses.get(
        f"{BASE_URL}/data/events/room/room_xyz",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_events("room_xyz", scope="room", limit=1000)
    assert len(df) == 3


@responses.activate
def test_get_events_participant_scope(api_key, events_response):
    """get_events with scope='participant' passes roomId query param."""
    responses.get(
        f"{BASE_URL}/data/events/participant/user_1",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_events("user_1", scope="participant", room_id="room_xyz", limit=1000)
    assert len(df) == 3
    # Verify roomId was passed as query param
    assert "roomId=room_xyz" in responses.calls[0].request.url


@responses.activate
def test_get_events_with_filters(api_key, events_response):
    """get_events passes filtering query params correctly."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.get_events(
        "exp_abc123",
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-12-31T23:59:59Z",
        category="component",
        sort="onset",
        order="desc",
        limit=100,
    )
    url = responses.calls[0].request.url
    assert "startTime=2024-01-01T00" in url
    assert "category=component" in url
    assert "sort=onset" in url
    assert "order=desc" in url
    assert "limit=100" in url


@responses.activate
def test_get_events_with_deployment_id(api_key, events_response):
    """get_events passes deploymentId query param when deployment_id is set."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.get_events("exp_abc123", deployment_id="dep_xyz", limit=100)
    url = responses.calls[0].request.url
    assert "deploymentId=dep_xyz" in url


@responses.activate
def test_get_participants_with_deployment_id(api_key, events_response):
    """get_participants passes deploymentId query param."""
    responses.get(
        f"{BASE_URL}/data/participants/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.get_participants("exp_abc123", deployment_id="dep_xyz", limit=100)
    url = responses.calls[0].request.url
    assert "deploymentId=dep_xyz" in url


@responses.activate
def test_deployment_id_omitted_when_none(api_key, events_response):
    """deployment_id=None should not add deploymentId to query params."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.get_events("exp_abc123", limit=100)
    url = responses.calls[0].request.url
    assert "deploymentId" not in url


# ------------------------------------------------------------------
# Data retrieval — other types
# ------------------------------------------------------------------


@responses.activate
def test_get_recordings(api_key, events_response):
    """get_recordings hits the correct endpoint."""
    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_recordings("exp_abc123", limit=1000)
    assert isinstance(df, pd.DataFrame)


@responses.activate
def test_get_ratings_continuous(api_key, events_response):
    """get_ratings builds the ratings/continuous path."""
    responses.get(
        f"{BASE_URL}/data/ratings/continuous/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_ratings("exp_abc123", kind="continuous", limit=1000)
    assert isinstance(df, pd.DataFrame)


@responses.activate
def test_get_ratings_sparse(api_key, events_response):
    """get_ratings with kind='sparse' builds the correct path."""
    responses.get(
        f"{BASE_URL}/data/ratings/sparse/room/room_xyz",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_ratings("room_xyz", kind="sparse", scope="room", limit=1000)
    assert isinstance(df, pd.DataFrame)


@responses.activate
def test_get_ratings_sparse_flattens_data(api_key, sparse_ratings_response):
    """Sparse ratings DataFrame contains flattened sparseRatingData columns."""
    responses.get(
        f"{BASE_URL}/data/ratings/sparse/experiment/exp_abc123",
        json=sparse_ratings_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_ratings("exp_abc123", kind="sparse", limit=1000)
    assert isinstance(df, pd.DataFrame)
    assert "sparseRatingData_mediaPauseOnset" in df.columns
    assert "sparseRatingData_mediaResumeOnset" in df.columns
    assert "sparseRatingData_actualPauseDuration" in df.columns
    assert "metadata_question" in df.columns
    assert df["sparseRatingData_mediaPauseOnset"].iloc[0] == 8200


@responses.activate
def test_get_sync_with_aggregation(api_key, events_response):
    """get_sync passes aggregationWindow param."""
    responses.get(
        f"{BASE_URL}/data/sync/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.get_sync("exp_abc123", aggregation_window=5000, limit=1000)
    assert "aggregationWindow=5000" in responses.calls[0].request.url


# ------------------------------------------------------------------
# download_recordings
# ------------------------------------------------------------------


@responses.activate
def test_download_recordings(api_key, recordings_response, tmp_path):
    """download_recordings writes files, CSV sidecar, and returns DataFrame."""
    # Mock the metadata API
    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=recordings_response,
        status=200,
    )
    # Mock the GCS signed URL downloads
    responses.get(
        recordings_response["data"][0]["downloadUrl"],
        body=b"fake video bytes",
        status=200,
    )
    responses.get(
        recordings_response["data"][1]["downloadUrl"],
        body=b"fake audio bytes",
        status=200,
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.download_recordings(
        "exp_abc123", output_dir=str(tmp_path), progress=False
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "local_path" in df.columns
    assert "download_status" in df.columns
    assert list(df["download_status"]) == ["downloaded", "downloaded"]

    # Files exist on disk
    assert (tmp_path / "Alice_video_EG_video_001.mp4").exists()
    assert (tmp_path / "Alice_audio_EG_audio_002.webm").exists()
    assert (tmp_path / "Alice_video_EG_video_001.mp4").read_bytes() == b"fake video bytes"

    # CSV sidecar written
    assert (tmp_path / "recordings_metadata.csv").exists()


@responses.activate
def test_download_recordings_filter_type(api_key, recordings_response, tmp_path):
    """recording_type filter limits downloads to matching type."""
    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=recordings_response,
        status=200,
    )
    responses.get(
        recordings_response["data"][1]["downloadUrl"],
        body=b"audio bytes",
        status=200,
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.download_recordings(
        "exp_abc123",
        output_dir=str(tmp_path),
        recording_type="audio",
        progress=False,
    )

    assert len(df) == 1
    assert (tmp_path / "Alice_audio_EG_audio_002.webm").exists()
    assert not (tmp_path / "Alice_video_EG_video_001.mp4").exists()


@responses.activate
def test_download_recordings_skip_existing(api_key, recordings_response, tmp_path):
    """Files with matching size are skipped."""
    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=recordings_response,
        status=200,
    )
    # Pre-create the video file with the expected size (1024 bytes)
    video_path = tmp_path / "Alice_video_EG_video_001.mp4"
    video_path.write_bytes(b"\x00" * 1024)

    # Only the audio file needs a mock download URL
    responses.get(
        recordings_response["data"][1]["downloadUrl"],
        body=b"\x00" * 512,
        status=200,
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.download_recordings(
        "exp_abc123", output_dir=str(tmp_path), progress=False
    )

    assert df["download_status"].iloc[0] == "skipped"
    assert df["download_status"].iloc[1] == "downloaded"


@responses.activate
def test_download_recordings_skip_requires_known_size(
    api_key, recordings_response, tmp_path
):
    """When server-side fileSize is missing, skip_existing must NOT accept a
    stale on-disk file — it must re-download so truncated prior attempts
    don't linger forever."""
    # Strip fileSize from the video record to simulate older recordings where
    # the backend didn't store file size metadata.
    recordings_response["data"][0]["fileSize"] = None

    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=recordings_response,
        status=200,
    )

    # Pre-create a (probably partial) video file on disk.
    video_path = tmp_path / "Alice_video_EG_video_001.mp4"
    video_path.write_bytes(b"stale-partial-content")

    fresh_video = b"freshly downloaded video bytes" * 20
    responses.get(
        recordings_response["data"][0]["downloadUrl"],
        body=fresh_video,
        status=200,
    )
    responses.get(
        recordings_response["data"][1]["downloadUrl"],
        body=b"audio",
        status=200,
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.download_recordings(
        "exp_abc123", output_dir=str(tmp_path), progress=False, skip_existing=True
    )

    assert df["download_status"].iloc[0] == "downloaded"
    assert video_path.read_bytes() == fresh_video


def test_download_recordings_list_call_uses_long_timeout(
    api_key, recordings_response, monkeypatch, tmp_path
):
    """The recordings-list call must use a longer timeout than the default
    30s API timeout, because signing many GCS URLs on the backend can easily
    push the listing latency past that."""
    captured_timeouts = []

    class FakeResp:
        status_code = 200
        ok = True
        reason = "OK"

        def json(self):
            return recordings_response

    def fake_request(method, url, **kwargs):
        captured_timeouts.append(kwargs.get("timeout"))
        return FakeResp()

    client = HyperStudy(api_key=api_key, base_url=BASE_URL, timeout=30)
    monkeypatch.setattr(client._transport._session, "request", fake_request)

    # Stub downloads so we don't need HTTP mocks for the signed URLs.
    import hyperstudy.client as client_mod

    monkeypatch.setattr(
        client_mod, "download_file", lambda url, dest, **kw: dest.write_bytes(b"") or 0
    )

    client.download_recordings(
        "exp_abc123", output_dir=str(tmp_path), progress=False, skip_existing=False
    )

    assert captured_timeouts, "no list call was made"
    # First captured timeout is the recordings-list call.
    assert captured_timeouts[0] is not None and captured_timeouts[0] >= 300, (
        f"expected list-call timeout >= 300s, got {captured_timeouts[0]}"
    )


@responses.activate
def test_download_recordings_raises_clear_error_on_list_failure(api_key, tmp_path):
    """A failure fetching recording metadata must surface a HyperStudyError
    that names the failing phase. Previously a bare ReadTimeout/ServerError
    leaked out, giving users no hint whether the list or a download failed."""
    from hyperstudy.exceptions import HyperStudyError

    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        status=504,
        json={
            "status": "error",
            "error": {"code": "GATEWAY_TIMEOUT", "message": "upstream timeout"},
        },
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with pytest.raises(HyperStudyError, match="[Ll]ist recordings"):
        client.download_recordings("exp_abc123", output_dir=str(tmp_path), progress=False)


@responses.activate
def test_download_recordings_warns_summary_on_partial_failure(
    api_key, recordings_response, tmp_path
):
    """When some files fail to download, a single summary warning must
    surface so interactive users see the failure count at a glance."""
    responses.get(
        f"{BASE_URL}/data/recordings/experiment/exp_abc123",
        json=recordings_response,
        status=200,
    )
    # Video download fails with 404; audio succeeds.
    responses.get(recordings_response["data"][0]["downloadUrl"], status=404)
    responses.get(
        recordings_response["data"][1]["downloadUrl"], body=b"audio", status=200
    )

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = client.download_recordings(
            "exp_abc123", output_dir=str(tmp_path), progress=False
        )

    messages = [str(w.message) for w in caught]
    assert any("1" in m and "2" in m and "failed" in m.lower() for m in messages), (
        f"expected a '1/2 failed' summary warning, got: {messages}"
    )
    assert list(df["download_status"]) == ["failed", "downloaded"]


@responses.activate
def test_download_recording_single(api_key, tmp_path):
    """download_recording downloads a single file."""
    url = "https://storage.example.com/rec.mp4"
    responses.get(url, body=b"video data", status=200)

    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    rec = {
        "recordingId": "EG_001",
        "participantName": "Bob",
        "downloadUrl": url,
        "format": "mp4",
        "metadata": {"type": "video"},
    }
    path = client.download_recording(rec, output_dir=str(tmp_path))

    assert path.exists()
    assert path.name == "Bob_video_EG_001.mp4"
    assert path.read_bytes() == b"video data"


# ------------------------------------------------------------------
# get_all_data
# ------------------------------------------------------------------


@responses.activate
def test_get_all_data(api_key, events_response, pre_experiment_response):
    """get_all_data returns a dict of DataFrames."""
    # Mock all data type endpoints for participant scope
    for dtype in ("events", "recordings", "chat", "videochat", "sync",
                  "ratings/continuous", "ratings/sparse", "components"):
        responses.get(
            f"{BASE_URL}/data/{dtype}/participant/user_1",
            json=events_response,
            status=200,
        )
    # Questionnaire, instructions, consent all hit the events endpoint
    # with different category params — responses matches by URL, so we
    # need a single mock for the events endpoint that handles all calls.
    # The events endpoint is already mocked above, so the category-filtered
    # calls will also match it.
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    result = client.get_all_data("user_1", room_id="room_xyz")

    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "events", "recordings", "chat", "videochat", "sync",
        "ratings_continuous", "ratings_sparse", "components",
        "questionnaire", "instructions", "consent",
    }
    for v in result.values():
        assert isinstance(v, pd.DataFrame)


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


@responses.activate
def test_401_raises_authentication_error(api_key, error_401):
    """A 401 response raises AuthenticationError."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=error_401,
        status=401,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with pytest.raises(AuthenticationError, match="Invalid or expired"):
        client.get_events("exp_abc123", limit=100)


@responses.activate
def test_403_raises_forbidden_error(api_key, error_403):
    """A 403 response raises ForbiddenError with details."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=error_403,
        status=403,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with pytest.raises(ForbiddenError, match="Insufficient scopes") as exc_info:
        client.get_events("exp_abc123", limit=100)
    assert exc_info.value.details["required"] == ["read:events"]


# ------------------------------------------------------------------
# Invalid scope
# ------------------------------------------------------------------


def test_invalid_scope_raises_value_error(api_key):
    """Passing an invalid scope string raises ValueError."""
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with pytest.raises(ValueError, match="invalid"):
        client.get_events("exp_abc123", scope="invalid", limit=100)


# ------------------------------------------------------------------
# Convenience methods — questionnaire, instructions, consent
# ------------------------------------------------------------------


@responses.activate
def test_get_questionnaire(api_key, events_response):
    """get_questionnaire passes category=questionnaire in the URL."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_questionnaire("exp_abc123", limit=1000)
    assert isinstance(df, pd.DataFrame)
    assert "category=questionnaire" in responses.calls[0].request.url


@responses.activate
def test_get_instructions_filters_by_event_type(api_key, pre_experiment_response):
    """get_instructions fetches pre_experiment events and filters to instructions."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=pre_experiment_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_instructions("exp_abc123", limit=1000)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # 2 instruction events out of 4 pre_experiment
    assert "category=pre_experiment" in responses.calls[0].request.url
    assert all(et.startswith("instructions.") for et in df["eventType"])


@responses.activate
def test_get_consent_filters_by_event_type(api_key, pre_experiment_response):
    """get_consent fetches pre_experiment events and filters to consent."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=pre_experiment_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_consent("exp_abc123", limit=1000)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # 2 consent events out of 4 pre_experiment
    assert all(et.startswith("consent.") for et in df["eventType"])


@responses.activate
def test_get_instructions_dict_output(api_key, pre_experiment_response):
    """get_instructions with output='dict' returns filtered list."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=pre_experiment_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    data = client.get_instructions("exp_abc123", output="dict", limit=1000)

    assert isinstance(data, list)
    assert len(data) == 2
    assert all(e["eventType"].startswith("instructions.") for e in data)


# ------------------------------------------------------------------
# Deployments
# ------------------------------------------------------------------


@responses.activate
def test_list_deployments(api_key, deployments_list_response):
    """list_deployments hits /deployments and returns a DataFrame."""
    responses.get(
        f"{BASE_URL}/deployments",
        json=deployments_list_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.list_deployments()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "dep_001" in df["id"].values


@responses.activate
def test_list_deployments_with_filters(api_key, deployments_list_response):
    """list_deployments passes experiment_id and status as query params."""
    responses.get(
        f"{BASE_URL}/deployments",
        json=deployments_list_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    client.list_deployments(experiment_id="exp_abc123", status="active")

    url = responses.calls[0].request.url
    assert "experimentId=exp_abc123" in url
    assert "status=active" in url


@responses.activate
def test_get_deployment(api_key, deployment_single_response):
    """get_deployment returns a single deployment dict."""
    responses.get(
        f"{BASE_URL}/deployments/dep_001",
        json=deployment_single_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    result = client.get_deployment("dep_001")

    assert isinstance(result, dict)
    assert result["id"] == "dep_001"
    assert result["name"] == "Pilot Study"


@responses.activate
def test_get_deployment_sessions(api_key, deployment_sessions_response):
    """get_deployment_sessions returns sessions as a DataFrame."""
    responses.get(
        f"{BASE_URL}/deployments/dep_001/sessions",
        json=deployment_sessions_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    df = client.get_deployment_sessions("dep_001")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "room_001" in df["id"].values


# ------------------------------------------------------------------
# API warnings
# ------------------------------------------------------------------


@responses.activate
def test_api_warnings_surfaced(api_key, warnings_response):
    """API _warnings in metadata are surfaced via Python warnings."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=warnings_response,
        status=200,
    )
    client = HyperStudy(api_key=api_key, base_url=BASE_URL)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.get_events("exp_abc123", limit=1000)

    assert len(caught) == 1
    assert "MISSING_INDEX" in str(caught[0].message)
