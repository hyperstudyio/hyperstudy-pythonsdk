"""DataFrame conversion for API response data."""

from __future__ import annotations

from typing import Any

import pandas as pd


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
