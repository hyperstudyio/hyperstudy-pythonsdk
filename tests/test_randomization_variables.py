"""V2 randomization clusters and variable definitions on experiments.

The v3 API accepts ``clusters`` and ``variableDefinitions`` on create and
update, states and groups join a cluster with ``clusterId``, and a TIMED state
draws its duration from a random variable with ``transitionRules.variableId``.
"""

from __future__ import annotations

import json

import pytest
import responses
from pydantic import ValidationError as PydanticValidationError

from hyperstudy import (
    Cluster,
    ClusterRule,
    Distribution,
    Experiment,
    Group,
    HyperStudy,
    State,
    TransitionRules,
    VariableDefinition,
    show_text,
)
from hyperstudy.exceptions import ValidationError

from .conftest import BASE_URL, envelope


def _sent(call_index: int = 0) -> dict:
    return json.loads(responses.calls[call_index].request.body)


def _randomized_experiment() -> Experiment:
    return Experiment(
        name="Randomized study",
        runtime="v2",
        randomize_states=True,
        clusters=[
            Cluster(id="block", name="Block", rule=ClusterRule(type="shuffle")),
            Cluster(id="inner", rule=ClusterRule(type="shuffle", across_groups="same")),
        ],
        variable_definitions=[
            VariableDefinition(
                id="v_end", name="endowment", kind="constant", value={"first_offer": 3}
            ),
            VariableDefinition(
                id="v_iti",
                name="iti_ms",
                kind="random",
                distribution=Distribution(type="uniform", min=500, max=1500),
                draw="per_use",
                round=0,
            ),
            VariableDefinition(
                id="v_pick",
                name="pick",
                kind="random",
                distribution=Distribution(
                    type="list",
                    values=[{"face_id": 1}, {"face_id": 2}],
                    sampling="without_replacement",
                ),
                draw="per_room",
            ),
            VariableDefinition(id="v_dbl", name="doubled", kind="computed", expr="endowment * 2"),
        ],
        states=[
            State(id="a", cluster_id="block", focus_component=show_text("A", id="fa")),
            State(id="b", cluster_id="block", focus_component=show_text("B", id="fb")),
            State(
                id="pause",
                focus_component=show_text("+", id="fp"),
                transition_rules=TransitionRules(type="TIMED", variable_id="v_iti"),
            ),
            State(id="g1", cluster_id="inner"),
            State(id="g2", cluster_id="inner"),
        ],
        groups=[Group(id="grp", name="Group", order=3, children=["g1", "g2"], cluster_id="block")],
    )


@responses.activate
def test_create_sends_clusters_and_variable_definitions_in_wire_format(api_key):
    responses.post(f"{BASE_URL}/experiments", json=envelope({"id": "exp-1"}), status=201)

    HyperStudy(api_key=api_key).create_experiment(experiment=_randomized_experiment())
    sent = _sent()

    assert sent["runtime"] == "v2"
    assert sent["randomizeStates"] is True
    assert sent["clusters"] == [
        {"id": "block", "name": "Block", "rule": {"type": "shuffle"}},
        {"id": "inner", "rule": {"type": "shuffle", "acrossGroups": "same"}},
    ]
    by_id = {v["id"]: v for v in sent["variableDefinitions"]}
    # A constant's value is researcher data: its keys are not camelCased.
    assert by_id["v_end"] == {
        "id": "v_end",
        "name": "endowment",
        "kind": "constant",
        "value": {"first_offer": 3},
    }
    assert by_id["v_iti"] == {
        "id": "v_iti",
        "name": "iti_ms",
        "kind": "random",
        "distribution": {"type": "uniform", "min": 500, "max": 1500},
        "draw": "per_use",
        "round": 0,
    }
    assert by_id["v_pick"]["distribution"]["values"] == [{"face_id": 1}, {"face_id": 2}]
    assert by_id["v_dbl"] == {
        "id": "v_dbl",
        "name": "doubled",
        "kind": "computed",
        "expr": "endowment * 2",
    }
    assert "variable_definitions" not in sent

    states = {s["id"]: s for s in sent["states"]}
    assert states["a"]["clusterId"] == "block"
    assert states["pause"]["transitionRules"] == {"type": "TIMED", "variableId": "v_iti"}
    assert sent["groups"] == [
        {"id": "grp", "name": "Group", "order": 3, "children": ["g1", "g2"], "clusterId": "block"}
    ]


@responses.activate
def test_update_kwargs_with_plain_dicts_convert_schema_keys_only(api_key):
    """Kwargs camelCase schema keys but keep a constant's value and list values as written."""
    responses.put(
        f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1", "updated": True}), status=200
    )

    result = HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        clusters=[{"id": "block", "rule": {"type": "keep", "across_groups": "independent"}}],
        variable_definitions=[
            {
                "id": "v1",
                "name": "prices",
                "kind": "constant",
                "value": {"base_price": 2, "max_price": 9},
            },
            {
                "id": "v2",
                "name": "cue",
                "kind": "random",
                "draw": "per_room",
                "distribution": {
                    "type": "list",
                    "values": [{"cue_side": "left"}],
                    "sampling": "sequential",
                },
            },
        ],
    )

    assert result == {"id": "exp-1", "updated": True}
    assert _sent() == {
        "clusters": [{"id": "block", "rule": {"type": "keep", "acrossGroups": "independent"}}],
        "variableDefinitions": [
            {
                "id": "v1",
                "name": "prices",
                "kind": "constant",
                "value": {"base_price": 2, "max_price": 9},
            },
            {
                "id": "v2",
                "name": "cue",
                "kind": "random",
                "draw": "per_room",
                "distribution": {
                    "type": "list",
                    "values": [{"cue_side": "left"}],
                    "sampling": "sequential",
                },
            },
        ],
    }


@responses.activate
def test_update_kwargs_accept_typed_models(api_key):
    responses.put(
        f"{BASE_URL}/experiments/exp-1", json=envelope({"id": "exp-1", "updated": True}), status=200
    )

    HyperStudy(api_key=api_key).update_experiment(
        "exp-1",
        clusters=[Cluster(id="c1", rule=ClusterRule(type="shuffle", across_groups="same"))],
        variable_definitions=[VariableDefinition(id="v1", name="n", kind="constant", value=[1, 2])],
    )

    assert _sent() == {
        "clusters": [{"id": "c1", "rule": {"type": "shuffle", "acrossGroups": "same"}}],
        "variableDefinitions": [{"id": "v1", "name": "n", "kind": "constant", "value": [1, 2]}],
    }


@responses.activate
def test_get_config_round_trips_through_the_typed_builder(api_key):
    """A definition read back from /config rebuilds into typed models and re-sends unchanged."""
    stored = Experiment.model_validate(
        _randomized_experiment().model_dump(by_alias=True, exclude_none=True)
    )
    record = {"id": "exp-1", **stored.model_dump(by_alias=True, exclude_none=True)}
    responses.get(f"{BASE_URL}/experiments/exp-1/config", json=envelope(record), status=200)

    config = HyperStudy(api_key=api_key).get_experiment_config("exp-1")

    assert config["clusters"][1]["rule"]["acrossGroups"] == "same"
    rebuilt = Experiment.model_validate(config)
    assert isinstance(rebuilt.clusters[0], Cluster)
    assert isinstance(rebuilt.variable_definitions[1], VariableDefinition)
    assert isinstance(rebuilt.variable_definitions[1].distribution, Distribution)
    assert rebuilt.states[2].transition_rules.variable_id == "v_iti"
    assert rebuilt.groups[0].cluster_id == "block"
    assert rebuilt.variable_definitions[0].value == {"first_offer": 3}
    dumped = rebuilt.model_dump(by_alias=True, exclude_none=True)
    dumped.pop("id")
    assert dumped == stored.model_dump(by_alias=True, exclude_none=True)


@responses.activate
def test_refused_randomization_raises_validation_error_with_reasons(api_key):
    responses.put(
        f"{BASE_URL}/experiments/exp-1",
        json={
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid randomization",
                "details": {"errors": ['cluster "c1" has unknown rule "sort"']},
            },
        },
        status=400,
    )

    with pytest.raises(ValidationError) as caught:
        HyperStudy(api_key=api_key).update_experiment(
            "exp-1", clusters=[{"id": "c1", "rule": {"type": "sort"}}]
        )

    assert caught.value.code == "VALIDATION_ERROR"
    assert caught.value.details["errors"] == ['cluster "c1" has unknown rule "sort"']


def test_generated_ids_let_a_timed_state_reference_its_variable():
    iti = VariableDefinition(
        name="iti_ms",
        kind="random",
        distribution=Distribution(type="exponential", mean=800, max=3000),
    )
    cluster = Cluster(rule=ClusterRule(type="shuffle"))
    assert iti.id and cluster.id and iti.id != cluster.id
    state = State(id="s", transition_rules=TransitionRules(type="TIMED", variable_id=iti.id))
    assert (
        state.model_dump(by_alias=True, exclude_none=True)["transitionRules"]["variableId"]
        == iti.id
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "1st", "kind": "constant", "value": 1},  # name starts with a digit
        {"name": "x", "kind": "random", "round": 7},  # more decimals than the server keeps
        {"name": "x", "kind": "computed", "expr": ""},  # empty expression
    ],
)
def test_variable_definition_rejects_what_the_server_would(kwargs):
    with pytest.raises(PydanticValidationError):
        VariableDefinition(**kwargs)


def test_distribution_rejects_non_positive_sd_and_empty_list():
    with pytest.raises(PydanticValidationError):
        Distribution(type="normal", mean=0, sd=0)
    with pytest.raises(PydanticValidationError):
        Distribution(type="list", values=[], sampling="sequential")


def test_too_many_clusters_fail_when_the_model_is_built():
    with pytest.raises(PydanticValidationError):
        Experiment(name="x", clusters=[Cluster(rule=ClusterRule(type="keep")) for _ in range(101)])
