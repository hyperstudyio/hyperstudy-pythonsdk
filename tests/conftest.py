"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASE_URL = "https://api.hyperstudy.io/api/v3"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def api_key():
    return "hst_test_abc123"


@pytest.fixture
def events_response():
    return load_fixture("events_response.json")


@pytest.fixture
def experiments_list_response():
    return load_fixture("experiments_list_response.json")


@pytest.fixture
def experiment_single_response():
    return load_fixture("experiment_single_response.json")


@pytest.fixture
def paginated_page1():
    return load_fixture("paginated_page1.json")


@pytest.fixture
def paginated_page2():
    return load_fixture("paginated_page2.json")


@pytest.fixture
def pre_experiment_response():
    return load_fixture("pre_experiment_response.json")


@pytest.fixture
def deployments_list_response():
    return load_fixture("deployments_list_response.json")


@pytest.fixture
def deployment_single_response():
    return load_fixture("deployment_single_response.json")


@pytest.fixture
def deployment_sessions_response():
    return load_fixture("deployment_sessions_response.json")


@pytest.fixture
def warnings_response():
    return load_fixture("warnings_response.json")


@pytest.fixture
def error_401():
    return load_fixture("error_401.json")


@pytest.fixture
def error_403():
    return load_fixture("error_403.json")


@pytest.fixture
@responses.activate
def client(api_key, base_url):
    """Create a HyperStudy client for testing.

    Note: this fixture activates `responses` so HTTP calls are mocked.
    Use it inside test functions that also use @responses.activate.
    """
    from hyperstudy import HyperStudy

    return HyperStudy(api_key=api_key, base_url=base_url)
