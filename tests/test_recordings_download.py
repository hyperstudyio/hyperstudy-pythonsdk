import responses
import hyperstudy


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
