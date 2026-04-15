"""Helpers for downloading recording files from signed URLs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

_CHUNK_SIZE = 65536  # 64 KB — good balance for large video files
_UNSAFE_RE = re.compile(r"[^\w\-]")


def get_download_url(recording: dict[str, Any]) -> str | None:
    """Return the best download URL from a recording dict, or ``None``."""
    return recording.get("downloadUrl") or recording.get("url") or None


def build_filename(recording: dict[str, Any]) -> str:
    """Build a filesystem-safe filename from recording metadata.

    Pattern: ``{participantName}_{type}_{recordingId}.{ext}``
    """
    name = recording.get("participantName") or recording.get("participantId") or "unknown"
    name = _UNSAFE_RE.sub("_", name)

    meta = recording.get("metadata") or {}
    rec_type = meta.get("type") or "recording"

    rec_id = recording.get("recordingId") or recording.get("egressId") or "unknown"

    fmt = recording.get("format")
    if not fmt:
        fmt = "webm" if rec_type == "audio" else "mp4"

    return f"{name}_{rec_type}_{rec_id}.{fmt}"


def download_file(url: str, dest: Path, timeout: int = 300) -> int:
    """Stream-download *url* to *dest* and return bytes written.

    Verifies ``Content-Length`` (when the server provides it) against bytes
    actually written. On any error — HTTP, mid-stream disconnect, or length
    mismatch — the partial file on disk is removed so ``skip_existing``
    logic won't mistake it for a complete download on retry.
    """
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    expected: int | None
    if "Content-Length" in resp.headers:
        try:
            expected = int(resp.headers["Content-Length"])
        except (TypeError, ValueError):
            expected = None
    else:
        expected = None

    written = 0
    # BaseException so Ctrl-C also cleans up, not just exceptions.
    try:
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=_CHUNK_SIZE):
                fh.write(chunk)
                written += len(chunk)

        if expected is not None and written != expected:
            raise IOError(
                f"Truncated download: wrote {written} of {expected} bytes for {dest.name}"
            )
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

    return written
