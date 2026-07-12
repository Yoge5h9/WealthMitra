from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.models import PersonaData, load_personas

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "personas"
REAL_SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"


def test_load_personas_returns_all_fixture_files_keyed_by_stem() -> None:
    personas = load_personas(FIXTURES_DIR)

    assert set(personas) == {"ravi", "priya"}
    assert all(isinstance(p, PersonaData) for p in personas.values())


def test_load_personas_parses_nested_fields() -> None:
    personas = load_personas(FIXTURES_DIR)

    ravi = personas["ravi"]
    assert ravi.profile.id == "ravi"
    assert ravi.profile.age == 28
    assert ravi.transactions[0].date == date(2026, 6, 1)
    assert ravi.transactions[0].type == "credit"
    assert ravi.external.aa_available is True
    assert ravi.external.holdings[0].institution == "HDFC AMC"


def test_load_personas_handles_no_aa_persona() -> None:
    personas = load_personas(FIXTURES_DIR)

    priya = personas["priya"]
    assert priya.external.aa_available is False
    assert priya.external.holdings == []
    assert priya.goals == []


def test_load_personas_rejects_malformed_persona(tmp_path: Path) -> None:
    bad = tmp_path / "broken.json"
    bad.write_text('{"profile": {"id": "broken"}}')  # missing required profile fields

    with pytest.raises(ValidationError):
        load_personas(tmp_path)


def test_load_personas_empty_dir_returns_empty_dict(tmp_path: Path) -> None:
    assert load_personas(tmp_path) == {}


def test_external_holding_rate_is_optional(tmp_path: Path) -> None:
    """Equity-type holdings have no fixed interest rate, unlike MF/FD/loans."""
    equity_persona = tmp_path / "equity_holder.json"
    equity_persona.write_text(
        """{
          "profile": {"id": "eq1", "name": "Equity Holder", "age": 40, "city": "Pune",
                       "segment": "hni", "language": "en", "risk_tolerance": "aggressive",
                       "dependents": 2, "occupation": "business", "avatar": "eq1.png", "story": "x"},
          "transactions": [],
          "goals": [],
          "external": {"aa_available": true, "connected": true,
                        "holdings": [{"id": "h1", "type": "equity", "institution": "Zerodha",
                                      "amount": 500000, "rate": null}],
                        "liabilities": []}
        }"""
    )

    personas = load_personas(tmp_path)

    assert personas["equity_holder"].external.holdings[0].rate is None


def test_load_personas_tolerates_legacy_extra_fields(tmp_path: Path) -> None:
    """Real persona files carry a few legacy keys beyond the base schema (city_tier,
    employment, idle_balance, ...); the loader must drop them, not reject the file."""
    persona = tmp_path / "legacy.json"
    persona.write_text(
        """{
          "profile": {"id": "legacy1", "name": "Legacy Case", "age": 50, "city": "Delhi",
                       "segment": "hni", "language": "en", "risk_tolerance": "moderate",
                       "dependents": 0, "occupation": "business", "avatar": "l.png", "story": "x",
                       "city_tier": 1, "employment": "self_employed", "idle_balance": 20000,
                       "fd_rate": 7.1},
          "transactions": [],
          "goals": [],
          "external": {"aa_available": false, "connected": false, "holdings": [], "liabilities": []}
        }"""
    )

    personas = load_personas(tmp_path)

    assert personas["legacy"].profile.id == "legacy1"
    assert not hasattr(personas["legacy"].profile, "city_tier")


@pytest.mark.skipif(not REAL_SYNTHETIC_DIR.is_dir(), reason="data/synthetic/ not present")
def test_load_personas_loads_all_real_synthetic_personas() -> None:
    personas = load_personas(REAL_SYNTHETIC_DIR)

    assert set(personas) == {"ravi", "shanta", "meera", "arjun", "vikram", "devika", "priya"}
