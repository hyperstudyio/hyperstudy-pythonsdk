"""Tests for DataFrame conversion (pandas and polars)."""

from __future__ import annotations

import pandas as pd
import pytest

from hyperstudy._dataframe import to_pandas, to_polars

SAMPLE_DATA = [
    {
        "id": "evt_001",
        "onset": 1500,
        "timestamp": "2024-06-15T10:00:01.500Z",
        "category": "component",
    },
    {
        "id": "evt_002",
        "onset": 3200,
        "timestamp": "2024-06-15T10:00:03.200Z",
        "category": "component",
    },
]


# ------------------------------------------------------------------
# Pandas
# ------------------------------------------------------------------


def test_to_pandas_creates_dataframe():
    df = to_pandas(SAMPLE_DATA)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2


def test_to_pandas_onset_sec():
    df = to_pandas(SAMPLE_DATA)
    assert "onset_sec" in df.columns
    assert df["onset_sec"].iloc[0] == pytest.approx(1.5)
    assert df["onset_sec"].iloc[1] == pytest.approx(3.2)


def test_to_pandas_timestamp_parsed():
    df = to_pandas(SAMPLE_DATA)
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_to_pandas_empty():
    df = to_pandas([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ------------------------------------------------------------------
# Polars
# ------------------------------------------------------------------


def test_to_polars_creates_dataframe():
    polars = pytest.importorskip("polars")
    df = to_polars(SAMPLE_DATA)
    assert isinstance(df, polars.DataFrame)
    assert len(df) == 2


def test_to_polars_onset_sec():
    pytest.importorskip("polars")
    df = to_polars(SAMPLE_DATA)
    assert "onset_sec" in df.columns
    assert df["onset_sec"][0] == pytest.approx(1.5)


def test_to_polars_empty():
    polars = pytest.importorskip("polars")
    df = to_polars([])
    assert isinstance(df, polars.DataFrame)
    assert len(df) == 0
