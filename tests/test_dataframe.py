"""Tests for DataFrame conversion (pandas and polars)."""

from __future__ import annotations

import pandas as pd
import pytest

from hyperstudy._dataframe import _flatten_nested_dicts, to_pandas, to_polars

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

SPARSE_RATING_DATA = [
    {
        "ratingId": "rat_001",
        "onset": 8500,
        "timestamp": "2024-06-15T10:01:30.000Z",
        "value": 72.5,
        "type": "sparse",
        "metadata": {
            "question": "How engaging?",
            "dimension": "engagement",
            "componentType": "vasrating",
        },
        "sparseRatingData": {
            "videoId": "video_abc",
            "pauseIndex": 0,
            "mediaPauseOnset": 8200,
            "mediaResumeOnset": 10800,
            "actualPauseDuration": 2600,
            "componentData": {"value": 58},
        },
    },
    {
        "ratingId": "rat_002",
        "onset": 25300,
        "timestamp": "2024-06-15T10:02:45.000Z",
        "value": 45.0,
        "type": "sparse",
        "metadata": {
            "question": "How engaging?",
            "dimension": "engagement",
            "componentType": "vasrating",
        },
        "sparseRatingData": {
            "videoId": "video_abc",
            "pauseIndex": 1,
            "mediaPauseOnset": 25000,
            "mediaResumeOnset": 27300,
            "actualPauseDuration": 2300,
            "componentData": {"value": 36},
        },
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


# ------------------------------------------------------------------
# Nested dict flattening
# ------------------------------------------------------------------


def test_flatten_sparse_rating_data():
    df = to_pandas(SPARSE_RATING_DATA)
    assert "sparseRatingData_mediaPauseOnset" in df.columns
    assert "sparseRatingData_mediaResumeOnset" in df.columns
    assert "sparseRatingData_actualPauseDuration" in df.columns
    assert "sparseRatingData_videoId" in df.columns
    assert "sparseRatingData_pauseIndex" in df.columns
    assert df["sparseRatingData_mediaPauseOnset"].iloc[0] == 8200
    assert df["sparseRatingData_mediaPauseOnset"].iloc[1] == 25000


def test_flatten_metadata():
    df = to_pandas(SPARSE_RATING_DATA)
    assert "metadata_question" in df.columns
    assert "metadata_dimension" in df.columns
    assert "metadata_componentType" in df.columns
    assert df["metadata_question"].iloc[0] == "How engaging?"


def test_flatten_preserves_original():
    df = to_pandas(SPARSE_RATING_DATA)
    assert "sparseRatingData" in df.columns
    assert isinstance(df["sparseRatingData"].iloc[0], dict)
    assert "metadata" in df.columns
    assert isinstance(df["metadata"].iloc[0], dict)


def test_flatten_handles_none():
    data = [
        {"ratingId": "r1", "onset": 100, "sparseRatingData": None, "metadata": None},
    ]
    df = to_pandas(data)
    assert "sparseRatingData" in df.columns
    # No flattened columns since the nested value is None, not a dict
    assert "sparseRatingData_mediaPauseOnset" not in df.columns


def test_flatten_no_target_fields():
    """Data without any flatten-target fields passes through unchanged."""
    result = _flatten_nested_dicts(SAMPLE_DATA)
    assert result is SAMPLE_DATA  # same object — no copy needed


def test_flatten_empty():
    result = _flatten_nested_dicts([])
    assert result == []


def test_flatten_polars():
    pytest.importorskip("polars")
    df = to_polars(SPARSE_RATING_DATA)
    assert "sparseRatingData_mediaPauseOnset" in df.columns
    assert "metadata_question" in df.columns
    assert df["sparseRatingData_mediaPauseOnset"][0] == 8200
