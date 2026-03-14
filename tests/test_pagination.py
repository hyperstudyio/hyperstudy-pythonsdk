"""Tests for auto-pagination."""

from __future__ import annotations

import responses

from hyperstudy import HyperStudy

BASE_URL = "https://api.hyperstudy.io/api/v3"


@responses.activate
def test_auto_pagination_fetches_all_pages(paginated_page1, paginated_page2):
    """When limit=None, the client auto-paginates through all pages."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=paginated_page1,
        status=200,
    )
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=paginated_page2,
        status=200,
    )

    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    df = client.get_events("exp_abc123", progress=False)

    # Should have fetched 3 + 2 = 5 records
    assert len(df) == 5
    assert df["id"].tolist() == ["evt_001", "evt_002", "evt_003", "evt_004", "evt_005"]
    # Two HTTP calls were made
    assert len(responses.calls) == 2


@responses.activate
def test_single_page_no_extra_requests(events_response):
    """When limit is set, only one request is made even if data has fewer items."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=events_response,
        status=200,
    )

    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    df = client.get_events("exp_abc123", limit=1000)

    assert len(df) == 3
    assert len(responses.calls) == 1


@responses.activate
def test_pagination_passes_offset(paginated_page1, paginated_page2):
    """Auto-pagination uses nextOffset from the API response."""
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=paginated_page1,
        status=200,
    )
    responses.get(
        f"{BASE_URL}/data/events/experiment/exp_abc123",
        json=paginated_page2,
        status=200,
    )

    client = HyperStudy(api_key="hst_test_key", base_url=BASE_URL)
    client.get_events("exp_abc123", progress=False)

    # Second request should have offset=3 (from nextOffset)
    second_url = responses.calls[1].request.url
    assert "offset=3" in second_url
