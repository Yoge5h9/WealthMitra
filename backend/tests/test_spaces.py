from pathlib import Path

import pytest

from app.core.spaces import DEFAULT_SPACE_ID, SpaceStore

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "personas"


@pytest.fixture
def store() -> SpaceStore:
    return SpaceStore(seed_dir=FIXTURES_DIR)


def test_create_space_returns_a_short_id(store: SpaceStore) -> None:
    space_id = store.create_space()

    assert isinstance(space_id, str)
    assert 0 < len(space_id) <= 16


def test_create_space_twice_yields_distinct_ids(store: SpaceStore) -> None:
    assert store.create_space() != store.create_space()


def test_get_unknown_space_raises_key_error(store: SpaceStore) -> None:
    with pytest.raises(KeyError):
        store.get("does-not-exist")


def test_new_space_is_seeded_with_personas(store: SpaceStore) -> None:
    space_id = store.create_space()

    space = store.get(space_id)

    assert set(space.personas) == {"ravi", "priya"}
    assert space.leads == []
    assert space.nudges == []
    assert space.sessions == {}
    assert space.audit == ()


def test_mutating_one_space_does_not_affect_another(store: SpaceStore) -> None:
    space_a_id = store.create_space()
    space_b_id = store.create_space()

    space_a = store.get(space_a_id)
    space_a.personas["ravi"].profile.name = "Mutated Name"
    space_a.leads.append("fake-lead")  # type: ignore[arg-type]
    space_a.sessions["s1"] = {"persona_id": "ravi"}

    space_b = store.get(space_b_id)
    assert space_b.personas["ravi"].profile.name == "Ravi Kumar"
    assert space_b.leads == []
    assert space_b.sessions == {}


def test_mutating_seed_personas_does_not_leak_into_new_spaces(store: SpaceStore) -> None:
    first = store.get(store.create_space())
    first.personas["ravi"].profile.name = "Mutated Name"

    second = store.get(store.create_space())

    assert second.personas["ravi"].profile.name == "Ravi Kumar"


def test_reset_restores_pristine_seed(store: SpaceStore) -> None:
    space_id = store.create_space()
    space = store.get(space_id)
    space.personas["ravi"].profile.name = "Mutated Name"
    space.leads.append("fake-lead")  # type: ignore[arg-type]

    store.reset(space_id)

    reset_space = store.get(space_id)
    assert reset_space.personas["ravi"].profile.name == "Ravi Kumar"
    assert reset_space.leads == []
    assert reset_space.id == space_id


def test_reset_unknown_space_raises_key_error(store: SpaceStore) -> None:
    with pytest.raises(KeyError):
        store.reset("does-not-exist")


def test_default_space_is_stable_across_calls(store: SpaceStore) -> None:
    first = store.default_space()
    first.sessions["s1"] = {"persona_id": "ravi"}

    second = store.default_space()

    assert second is first
    assert second.id == DEFAULT_SPACE_ID
    assert second.sessions == {"s1": {"persona_id": "ravi"}}
