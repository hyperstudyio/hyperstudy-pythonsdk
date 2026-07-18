"""Tests for persona CRUD methods and the Persona model."""

from __future__ import annotations

import json

import pandas as pd
import pytest
import responses

from hyperstudy import Guardrails, HyperStudy, Persona, PromptLayer

from .conftest import BASE_URL


@pytest.fixture
def api_key():
    return "hst_test_abc123"


PERSONA_DOC = {
    "id": "persona-1",
    "name": "Curious Undergrad",
    "description": "Warm and curious",
    "provider": "anthropic",
    "model": "claude-opus-4-8",
    "prompt": {"persona": "You are curious.", "objective": "", "guidance": "", "examples": [], "additionalInstructions": ""},
    "guardrails": {"maxTurns": 50, "budgetUsd": 2},
    "ownerId": "user-1",
}


def _envelope(data):
    return {"status": "success", "data": data, "metadata": {}}


@responses.activate
def test_list_personas(api_key):
    responses.get(f"{BASE_URL}/personas", json=_envelope([PERSONA_DOC]), status=200)

    client = HyperStudy(api_key=api_key)
    df = client.list_personas()

    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["name"] == "Curious Undergrad"


@responses.activate
def test_get_persona(api_key):
    responses.get(f"{BASE_URL}/personas/persona-1", json=_envelope(PERSONA_DOC), status=200)

    client = HyperStudy(api_key=api_key)
    persona = client.get_persona("persona-1")
    assert persona["id"] == "persona-1"


@responses.activate
def test_create_persona_typed_builder_camelizes(api_key):
    responses.post(f"{BASE_URL}/personas", json=_envelope(PERSONA_DOC), status=201)

    client = HyperStudy(api_key=api_key)
    persona = Persona(
        name="Curious Undergrad",
        provider="anthropic",
        model="claude-opus-4-8",
        prompt=PromptLayer(persona="You are curious.", additional_instructions="Stay warm."),
        guardrails=Guardrails(max_turns=50, budget_usd=2.0),
        memory_persistence="none",
    )
    created = client.create_persona(persona=persona)

    assert created["id"] == "persona-1"
    sent = json.loads(responses.calls[0].request.body)
    # snake_case fields camelized on the wire
    assert sent["memoryPersistence"] == "none"
    assert sent["guardrails"] == {"maxTurns": 50, "budgetUsd": 2.0}
    assert sent["prompt"]["additionalInstructions"] == "Stay warm."


@responses.activate
def test_create_persona_kwargs(api_key):
    responses.post(f"{BASE_URL}/personas", json=_envelope(PERSONA_DOC), status=201)

    client = HyperStudy(api_key=api_key)
    client.create_persona(name="Kwarg Agent", memory_persistence="cross-experiment")

    sent = json.loads(responses.calls[0].request.body)
    assert sent["name"] == "Kwarg Agent"
    assert sent["memoryPersistence"] == "cross-experiment"


def test_create_persona_requires_name(api_key):
    client = HyperStudy(api_key=api_key)
    with pytest.raises(ValueError, match="name"):
        client.create_persona(provider="anthropic")


@responses.activate
def test_update_persona_merge_patch_sends_only_given_fields(api_key):
    responses.put(f"{BASE_URL}/personas/persona-1", json=_envelope(PERSONA_DOC), status=200)

    client = HyperStudy(api_key=api_key)
    client.update_persona("persona-1", description="Updated")

    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"description": "Updated"}


def test_update_persona_requires_fields(api_key):
    client = HyperStudy(api_key=api_key)
    with pytest.raises(ValueError, match="No fields"):
        client.update_persona("persona-1")


@responses.activate
def test_create_persona_strips_offline_cognition(api_key):
    """offlineCognition is never sent — the server hard-discards it.

    Covers both a Persona rebuilt from an older API response (extra field)
    and the snake_case kwargs path. Offline loops now live inside
    cognition.config.contexts.<name>.offline."""
    responses.post(f"{BASE_URL}/personas", json=_envelope(PERSONA_DOC), status=201)
    responses.post(f"{BASE_URL}/personas", json=_envelope(PERSONA_DOC), status=201)

    client = HyperStudy(api_key=api_key)

    # Persona rebuilt from an older response doc carrying offlineCognition.
    persona = Persona(**{
        "name": "Rebuilt",
        "cognition": {"config": {"contexts": {"social": {"offline": {"cadence": "endOfState"}}}}},
        "offlineCognition": {"loops": []},
    })
    client.create_persona(persona=persona)
    sent = json.loads(responses.calls[0].request.body)
    assert "offlineCognition" not in sent
    assert "offline_cognition" not in sent
    assert sent["cognition"]["config"]["contexts"]["social"]["offline"] == {
        "cadence": "endOfState"
    }

    # Snake_case kwargs path.
    client.create_persona(name="Kwargs", offline_cognition={"loops": []})
    sent = json.loads(responses.calls[1].request.body)
    assert "offlineCognition" not in sent
    assert "offline_cognition" not in sent


@responses.activate
def test_update_persona_strips_offline_cognition(api_key):
    """update_persona also drops offlineCognition from the payload."""
    responses.put(f"{BASE_URL}/personas/persona-1", json=_envelope(PERSONA_DOC), status=200)

    client = HyperStudy(api_key=api_key)
    client.update_persona("persona-1", description="Updated", offline_cognition={"loops": []})

    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"description": "Updated"}


def test_persona_model_has_no_offline_cognition_field():
    """The typed Persona model no longer declares offline_cognition."""
    assert "offline_cognition" not in Persona.model_fields


@responses.activate
def test_get_cognition_catalog(api_key):
    """get_cognition_catalog returns the abilities/recipes/offlineRecipes dict."""
    catalog = {
        "abilities": {"perceive": {"description": "..."}},
        "recipes": {"default": ["perceive"]},
        "offlineRecipes": {"consolidate": ["reflect"]},
    }
    # The v3 envelope array-wraps non-array data; the client unwraps it.
    responses.get(
        f"{BASE_URL}/agent-cognition/catalog", json=_envelope([catalog]), status=200
    )

    client = HyperStudy(api_key=api_key)
    result = client.get_cognition_catalog()

    assert result == catalog
    assert set(result.keys()) == {"abilities", "recipes", "offlineRecipes"}


@responses.activate
def test_delete_and_duplicate_persona(api_key):
    responses.delete(f"{BASE_URL}/personas/persona-1", json=_envelope({"deleted": True}), status=200)
    responses.post(
        f"{BASE_URL}/personas/persona-1/duplicate",
        json=_envelope({**PERSONA_DOC, "id": "persona-2", "name": "Curious Undergrad (copy)"}),
        status=201,
    )

    client = HyperStudy(api_key=api_key)
    client.delete_persona("persona-1")
    copy = client.duplicate_persona("persona-1")
    assert copy["name"] == "Curious Undergrad (copy)"
