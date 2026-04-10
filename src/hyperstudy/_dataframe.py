"""DataFrame conversion for API response data."""

from __future__ import annotations

from typing import Any

import pandas as pd

# Nested dict fields to flatten into top-level columns.
# Mapping of {field_name: prefix} — sub-keys become ``{prefix}_{sub_key}``.
FLATTEN_FIELDS: dict[str, str] = {
    "sparseRatingData": "sparseRatingData",
    "metadata": "metadata",
}


def _flatten_nested_dicts(
    data: list[dict[str, Any]],
    fields: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Promote sub-keys of nested dict fields to top-level keys.

    For each *field* present in a record whose value is a ``dict``, every
    sub-key is copied to ``{prefix}_{sub_key}``.  The original nested dict
    is preserved for backward compatibility.

    Records where the target field is ``None`` or missing are left
    untouched — downstream DataFrame construction fills those columns
    with ``NaN`` / ``null``.
    """
    if not data:
        return data

    fields = fields if fields is not None else FLATTEN_FIELDS

    # Quick check on first record — skip work when no target fields exist.
    sample = data[0]
    targets = [f for f in fields if f in sample and isinstance(sample[f], dict)]
    if not targets:
        return data

    out: list[dict[str, Any]] = []
    for record in data:
        record = dict(record)  # shallow copy to avoid mutating caller's data
        for field in targets:
            nested = record.get(field)
            if isinstance(nested, dict):
                prefix = fields[field]
                for sub_key, sub_val in nested.items():
                    record[f"{prefix}_{sub_key}"] = sub_val
        out.append(record)
    return out


def _post_process(df: pd.DataFrame) -> pd.DataFrame:
    """Shared post-processing for pandas DataFrames.

    * Parses timestamp columns to datetime.
    * Computes ``onset_sec`` from ``onset`` (ms -> s).
    """
    if df.empty:
        return df

    # Parse common timestamp columns
    for col in ("timestamp", "startTime", "endTime", "createdAt", "updatedAt"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Compute onset in seconds
    if "onset" in df.columns:
        df["onset_sec"] = pd.to_numeric(df["onset"], errors="coerce") / 1000.0

    return df


def to_pandas(data: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert API response data to a pandas DataFrame with post-processing."""
    if not data:
        return pd.DataFrame()
    data = _flatten_nested_dicts(data)
    df = pd.DataFrame(data)
    return _post_process(df)


def to_polars(data: list[dict[str, Any]]):
    """Convert API response data to a polars DataFrame.

    Raises ImportError with a helpful message if polars is not installed.
    """
    try:
        import polars as pl
    except ImportError:
        raise ImportError(
            "polars is not installed. Install it with: pip install hyperstudy[polars]"
        ) from None

    if not data:
        return pl.DataFrame()

    data = _flatten_nested_dicts(data)
    df = pl.DataFrame(data)

    # Parse timestamps
    for col in ("timestamp", "startTime", "endTime", "createdAt", "updatedAt"):
        if col in df.columns:
            try:
                df = df.with_columns(pl.col(col).str.to_datetime(strict=False).alias(col))
            except Exception:
                pass  # Column may already be datetime or have unexpected format

    # Compute onset_sec
    if "onset" in df.columns:
        df = df.with_columns((pl.col("onset").cast(pl.Float64) / 1000.0).alias("onset_sec"))

    return df
