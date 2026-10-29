"""Tests for the HttpTransport wrapper."""

from __future__ import annotations

import pytest

from hyperstudy._http import HttpTransport


class _FakeResponse:
    status_code = 200
    ok = True
    reason = "OK"

    def json(self):
        return {"status": "success", "data": [], "metadata": {}}


def _make_transport(timeout=30):
    return HttpTransport(api_key="hst_test_key", timeout=timeout)


def test_get_uses_instance_timeout_by_default(monkeypatch):
    transport = _make_transport(timeout=30)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(transport._session, "request", fake_request)

    transport.get("/data/ping")

    assert captured["timeout"] == 30


def test_get_accepts_per_call_timeout_override(monkeypatch):
    """A per-call timeout must override the instance default without
    mutating it — critical so download_recordings can give the list call
    a longer window than other API calls."""
    transport = _make_transport(timeout=30)
    captured = []

    def fake_request(method, url, **kwargs):
        captured.append(kwargs)
        return _FakeResponse()

    monkeypatch.setattr(transport._session, "request", fake_request)

    transport.get("/data/slow", timeout=300)
    transport.get("/data/normal")

    assert captured[0]["timeout"] == 300
    assert captured[1]["timeout"] == 30
    assert transport.timeout == 30  # unchanged


def test_single_record_rejects_an_empty_array():
    """A single-object route answering with no object is an error, not an empty record."""
    from hyperstudy._http import single_record
    from hyperstudy.exceptions import HyperStudyError

    assert single_record({"data": [{"id": "x"}]}) == {"id": "x"}
    with pytest.raises(HyperStudyError, match="no record"):
        single_record({"data": []})


def test_single_record_rejects_a_null_record():
    from hyperstudy._http import single_record
    from hyperstudy.exceptions import HyperStudyError

    with pytest.raises(HyperStudyError, match="no record"):
        single_record({"data": [None]})
