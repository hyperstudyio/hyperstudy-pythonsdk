"""Tests for recording download helpers."""

from __future__ import annotations

import pytest
import responses

from hyperstudy._downloads import build_filename, download_file

# ------------------------------------------------------------------
# build_filename
# ------------------------------------------------------------------


VIDEO_RECORDING = {
    "recordingId": "EG_video_001",
    "participantName": "Alice",
    "format": "mp4",
    "metadata": {"type": "video"},
}

AUDIO_RECORDING = {
    "recordingId": "EG_audio_002",
    "participantName": "Alice",
    "format": "webm",
    "metadata": {"type": "audio"},
}


def test_build_filename_video():
    assert build_filename(VIDEO_RECORDING) == "Alice_video_EG_video_001.mp4"


def test_build_filename_audio():
    assert build_filename(AUDIO_RECORDING) == "Alice_audio_EG_audio_002.webm"


def test_build_filename_missing_fields():
    rec = {"egressId": "EG_123"}
    name = build_filename(rec)
    assert name == "unknown_recording_EG_123.mp4"


def test_build_filename_sanitizes_name():
    rec = {
        "recordingId": "EG_001",
        "participantName": "Alice O'Brien (test)",
        "format": "mp4",
        "metadata": {"type": "video"},
    }
    name = build_filename(rec)
    assert name == "Alice_O_Brien__test__video_EG_001.mp4"
    # No special characters remain
    assert "'" not in name
    assert "(" not in name


def test_build_filename_uses_participant_id_fallback():
    rec = {
        "recordingId": "EG_001",
        "participantId": "user_42",
        "format": "mp4",
        "metadata": {"type": "video"},
    }
    assert build_filename(rec) == "user_42_video_EG_001.mp4"


def test_build_filename_audio_default_format():
    """Audio recording with no format field defaults to webm."""
    rec = {
        "recordingId": "EG_001",
        "participantName": "Bob",
        "metadata": {"type": "audio"},
    }
    assert build_filename(rec).endswith(".webm")


# ------------------------------------------------------------------
# download_file
# ------------------------------------------------------------------


@responses.activate
def test_download_file(tmp_path):
    url = "https://storage.example.com/file.mp4"
    content = b"fake video content " * 100
    responses.get(url, body=content, status=200)

    dest = tmp_path / "output.mp4"
    written = download_file(url, dest)

    assert dest.exists()
    assert dest.read_bytes() == content
    assert written == len(content)


@responses.activate
def test_download_file_raises_on_error(tmp_path):
    url = "https://storage.example.com/missing.mp4"
    responses.get(url, status=404)

    dest = tmp_path / "output.mp4"
    with pytest.raises(Exception):
        download_file(url, dest)


@responses.activate
def test_download_file_detects_content_length_mismatch(tmp_path):
    """If the response ends with fewer bytes than Content-Length advertised,
    an error must propagate AND the partial file must be removed so it can't
    be mistaken for a complete download on retry."""
    url = "https://storage.example.com/truncated.mp4"
    short_body = b"only-1kb" * 128  # 1024 bytes
    # Lie about the length: claim 10x larger than what we send.
    responses.get(
        url,
        body=short_body,
        status=200,
        headers={"Content-Length": str(len(short_body) * 10)},
    )

    dest = tmp_path / "truncated.mp4"
    with pytest.raises(Exception):
        download_file(url, dest)

    assert not dest.exists(), "partial file must be deleted on truncation"


def test_download_file_raises_on_short_body_without_protocol_error(tmp_path, monkeypatch):
    """Guards the explicit Content-Length check: when the HTTP layer itself
    does NOT detect a short body (e.g. server closes cleanly after fewer
    bytes than advertised), download_file must still raise and clean up."""

    class ShortResponse:
        status_code = 200
        headers = {"Content-Length": "1000"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            # Deliberately yield fewer bytes than Content-Length claims,
            # then stop cleanly — urllib3 won't notice.
            yield b"x" * 10

    import hyperstudy._downloads as downloads_mod

    monkeypatch.setattr(
        downloads_mod.requests, "get", lambda *a, **kw: ShortResponse()
    )

    dest = tmp_path / "short.mp4"
    with pytest.raises(IOError, match="[Tt]runcated"):
        download_file("https://example.com/short.mp4", dest)

    assert not dest.exists()


@responses.activate
def test_download_file_cleans_up_on_stream_error(tmp_path):
    """If iter_content raises mid-stream, the partial file must be removed."""
    url = "https://storage.example.com/explode.mp4"

    class ExplodingResponse:
        status_code = 200
        headers: dict = {}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"first-chunk"
            raise ConnectionError("simulated network drop")

    import hyperstudy._downloads as downloads_mod

    def fake_get(url, stream, timeout):  # noqa: ARG001
        return ExplodingResponse()

    original = downloads_mod.requests.get
    downloads_mod.requests.get = fake_get
    try:
        dest = tmp_path / "explode.mp4"
        with pytest.raises(ConnectionError):
            download_file(url, dest)
        assert not dest.exists(), "partial file must be deleted on mid-stream error"
    finally:
        downloads_mod.requests.get = original
