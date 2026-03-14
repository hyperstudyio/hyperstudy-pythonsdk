"""Auto-pagination with progress bars for multi-page fetches."""

from __future__ import annotations

from typing import Any

from tqdm.auto import tqdm

from ._http import HttpTransport


def fetch_all_pages(
    transport: HttpTransport,
    path: str,
    params: dict[str, Any] | None = None,
    *,
    page_size: int = 1000,
    progress: bool = True,
) -> tuple[list[dict], dict]:
    """Fetch every page of a paginated endpoint.

    Returns:
        (all_data, last_metadata) — the combined list plus the metadata
        dict from the final page (useful for inspecting total counts, etc.).
    """
    params = dict(params or {})
    params["limit"] = page_size
    params.setdefault("offset", 0)

    # First request to learn total
    body = transport.get(path, params=params)
    metadata = body.get("metadata", {})
    pagination = metadata.get("pagination", {})
    total = pagination.get("total", 0)
    all_data: list[dict] = body.get("data", [])

    has_more = pagination.get("hasMore", False)

    bar = None
    if progress and total > page_size:
        bar = tqdm(total=total, desc="Fetching", unit=" rows", initial=len(all_data))

    while has_more:
        params["offset"] = pagination.get("nextOffset", params["offset"] + page_size)

        body = transport.get(path, params=params)
        metadata = body.get("metadata", {})
        pagination = metadata.get("pagination", {})

        page_data = body.get("data", [])
        all_data.extend(page_data)
        has_more = pagination.get("hasMore", False)

        if bar is not None:
            bar.update(len(page_data))

    if bar is not None:
        bar.update(bar.total - bar.n)  # snap to 100 %
        bar.close()

    return all_data, metadata
