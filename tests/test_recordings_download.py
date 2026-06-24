import warnings
from pathlib import Path

import pytest
import responses
import hyperstudy

BASE_URL = "https://api.hyperstudy.io/api/v3"


# ---------------------------------------------------------------------------
# Fix D — skip_existing when fileSize is unknown
# ---------------------------------------------------------------------------


@responses.activate
def test_skip_existing_no_filesize(tmp_path):
    """When fileSize is absent and file already exists, skip without re-downloading."""
    # Register the list-recordings endpoint
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/recordings/experiment/exp1",
        json={
            "status": "success",
            "metadata": {"total": 1, "limit": 50, "offset": 0, "dataType": "recordings"},
            "data": [
                {
                    "recordingId": "EG_001",
                    "participantName": "Alice",
                    "format": "mp4",
                    "metadata": {"type": "video"},
                    "downloadPath": "/data/recordings/download/room_1/EG_001",
                    # No fileSize key
                }
            ],
        },
        status=200,
    )

    dest_dir = tmp_path
    dest = dest_dir / "Alice_video_EG_001.mp4"
    dest.write_bytes(b"EXISTING_CONTENT")

    hs = hyperstudy.HyperStudy(api_key="hst_test_" + "a" * 32)

    df = hs.download_recordings("exp1", output_dir=str(dest_dir), skip_existing=True)

    # No download call should have been made for the GCS URL
    download_calls = [c for c in responses.calls if "signed" in c.request.url]
    assert len(download_calls) == 0, "Should have skipped the download"

    assert df["download_status"].iloc[0] == "skipped"
    # Pre-existing file must be intact
    assert dest.read_bytes() == b"EXISTING_CONTENT"


@responses.activate
def test_redownload_on_filesize_mismatch(tmp_path):
    """When fileSize is present but mismatched, re-download the file."""
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/recordings/experiment/exp2",
        json={
            "status": "success",
            "metadata": {"total": 1, "limit": 50, "offset": 0, "dataType": "recordings"},
            "data": [
                {
                    "recordingId": "EG_002",
                    "participantName": "Bob",
                    "format": "mp4",
                    "metadata": {"type": "video"},
                    "downloadPath": "/data/recordings/download/room_2/EG_002",
                    "fileSize": 9999,  # mismatch with existing file
                }
            ],
        },
        status=200,
    )
    # mint endpoint
    responses.add(
        responses.GET,
        f"{BASE_URL}/data/recordings/download/room_2/EG_002",
        json={"status": "success", "data": {"url": "https://signed.example/Bob.mp4"}},
        status=200,
    )
    # GCS signed URL
    new_bytes = b"NEW_DOWNLOAD_CONTENT"
    responses.add(
        responses.GET,
        "https://signed.example/Bob.mp4",
        body=new_bytes,
        status=200,
    )

    dest_dir = tmp_path
    dest = dest_dir / "Bob_video_EG_002.mp4"
    dest.write_bytes(b"OLD")  # size 3, doesn't match fileSize=9999

    hs = hyperstudy.HyperStudy(api_key="hst_test_" + "a" * 32)
    df = hs.download_recordings("exp2", output_dir=str(dest_dir), skip_existing=True)

    assert df["download_status"].iloc[0] == "downloaded"
    assert dest.read_bytes() == new_bytes


@responses.activate
def test_download_recording_mints_signed_url(tmp_path):
    base = "https://api.hyperstudy.io/api/v3"
    # 1) mint endpoint returns a signed url in the envelope
    responses.add(
        responses.GET,
        f"{base}/data/recordings/download/room_EXP_1_a/EG_x",
        json={"status": "success", "data": {"url": "https://signed.example/x.mp4"}},
        status=200,
    )
    # 2) the signed url serves bytes
    responses.add(responses.GET, "https://signed.example/x.mp4", body=b"VIDEOBYTES", status=200)

    hs = hyperstudy.HyperStudy(api_key="hst_test_" + "a" * 32)
    rec = {
        "downloadPath": "/data/recordings/download/room_EXP_1_a/EG_x",
        "fileName": "x.mp4",
        "participantId": "p1",
        "recordingId": "EG_x",
    }
    dest = hs.download_recording(rec, output_dir=str(tmp_path))
    assert dest.read_bytes() == b"VIDEOBYTES"


@responses.activate
def test_download_recording_falls_back_to_legacy_url(tmp_path):
    responses.add(responses.GET, "https://legacy.example/y.mp4", body=b"LEGACY", status=200)
    hs = hyperstudy.HyperStudy(api_key="hst_test_" + "a" * 32)
    rec = {"url": "https://legacy.example/y.mp4", "fileName": "y.mp4", "recordingId": "old"}
    dest = hs.download_recording(rec, output_dir=str(tmp_path))
    assert dest.read_bytes() == b"LEGACY"
