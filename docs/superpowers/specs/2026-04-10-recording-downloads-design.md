# Recording Downloads via Python SDK

## Problem

The Python SDK's `get_recordings()` returns metadata only. Users need the actual audio/video files for offline analysis (ML models, manual review, archival). Currently they must manually extract `downloadUrl` from each record and fetch files themselves.

## Decision: SDK-only, no backend changes

The V3 API already returns signed GCS download URLs (7-day expiry) in the recording metadata. The SDK will fetch metadata and download files in the same call, so URL expiry is not a practical concern. This matches how the frontend downloads recordings.

## API Surface

### `download_recordings()` — Bulk download

```python
df = hs.download_recordings(
    "exp_abc123",
    output_dir="./data/recordings",
    scope="experiment",           # "experiment" | "room" | "participant"
    deployment_id=None,           # optional filter
    room_id=None,                 # optional filter
    recording_type=None,          # "audio" | "video" | None (both)
    progress=True,                # tqdm progress bar
    skip_existing=True,           # skip files already on disk with matching size
)
```

**Returns**: `pandas.DataFrame` with all recording metadata columns plus:
- `local_path` — absolute path to the downloaded file on disk
- `download_status` — `"downloaded"`, `"skipped"`, or `"failed"`

**Side effects**:
- Writes media files to `output_dir`
- Writes `recordings_metadata.csv` to `output_dir`

### `download_recording()` — Single recording

```python
path = hs.download_recording(
    recording,                    # dict from get_recordings(output="dict")
    output_dir="./data/recordings",
)
```

**Returns**: `pathlib.Path` to downloaded file.

## Directory Structure

```
output_dir/
  recordings_metadata.csv
  user1_video_EG_abc123.mp4
  user1_audio_EG_def456.webm
  user2_video_EG_ghi789.mp4
```

**Filename pattern**: `{participantName}_{recordingType}_{recordingId}.{ext}`

- `participantName`: from recording metadata, sanitized for filesystem safety
- `recordingType`: `"video"` or `"audio"` from `metadata.type`
- `recordingId`: egressId or recordingId
- `ext`: from `format` field, falling back to `mp4` (video) or `webm` (audio)

## Internal Design

### Download flow (`download_recordings`)

1. Call `self.get_recordings(scope_id, scope=scope, output="dict")` to get metadata
2. Filter by `recording_type` if specified (via `metadata.type`)
3. Create `output_dir` via `os.makedirs(exist_ok=True)`
4. For each recording:
   - Build filename using pattern above
   - If `skip_existing=True` and file exists with size matching `fileSize` metadata, mark as `"skipped"`
   - Otherwise, fetch from `downloadUrl` (fallback: `url`) using streaming HTTP GET
   - Write to disk in 8KB chunks
   - Mark as `"downloaded"` or `"failed"` (with warning logged)
5. Build DataFrame from metadata, add `local_path` and `download_status` columns
6. Write `recordings_metadata.csv` to `output_dir`
7. Return DataFrame

### Streaming downloads

Use `requests.get(url, stream=True)` with chunked iteration to avoid loading large video files into memory. The SDK's existing `HttpTransport` handles JSON responses only, so file downloads use a standalone `requests.get()` — the signed GCS URLs don't need API key auth.

### Error handling

- Per-file failure tolerance: if one recording fails (404, timeout, network error), log a warning, set `download_status="failed"`, continue with remaining files
- If the metadata API call itself fails, raise normally (same as `get_recordings()`)
- Invalid/missing `downloadUrl`: set `download_status="failed"`, log warning

### Skip-existing logic

Compare `os.path.getsize(local_path)` against `fileSize` from metadata. If `fileSize` is `None` (metadata missing), fall back to checking file existence only (any existing file is considered complete).

## File Layout

| File | Change |
|------|--------|
| `src/hyperstudy/_downloads.py` | **New.** `build_filename()`, `download_file()` streaming helper |
| `src/hyperstudy/client.py` | Add `download_recordings()` and `download_recording()` methods |
| `tests/test_downloads.py` | **New.** Unit tests for filename building, skip logic, status tracking |
| `tests/test_client.py` | Integration test: mock API + GCS, verify files + DataFrame |
| `tests/fixtures/sparse_ratings_response.json` | Already exists (from prior work) |

## Testing

### Unit tests (`tests/test_downloads.py`)
- `test_build_filename` — video, audio, missing fields, filesystem-unsafe characters
- `test_build_filename_dedup` — duplicate names get numeric suffix
- `test_skip_existing_matching_size` — file with correct size is skipped
- `test_skip_existing_wrong_size` — file with wrong size is re-downloaded

### Integration tests (`tests/test_client.py`)
- `test_download_recordings` — mock API + GCS fetch, verify files on disk, CSV sidecar, DataFrame with `local_path` + `download_status`
- `test_download_recordings_filter_type` — `recording_type="audio"` only downloads audio
- `test_download_recording_single` — single recording download

### Mocking strategy
- V3 API: `responses` library (existing pattern)
- GCS signed URL: also `responses` (it's just an HTTP GET to a URL)
- File I/O: real writes to `pytest` `tmp_path`

## No Backend Changes Required

The existing V3 API endpoints return all necessary data:
- `GET /api/v3/data/recordings/{scope}/{scopeId}` returns metadata with `downloadUrl`
- Signed GCS URLs are valid for 7 days
- SDK downloads immediately after fetching metadata, so expiry is not an issue
