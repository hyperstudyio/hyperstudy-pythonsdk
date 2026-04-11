"""Tests for recording download helpers."""

from __future__ import annotations

import responses
import pytest

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
