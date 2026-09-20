from app.engines.change_understanding_engine import (
    ChangeUnderstandingEngine,
)


def test_rate_freshness_change() -> None:
    engine = ChangeUnderstandingEngine()

    result = engine.analyze(
        (
            "If we change the rate-freshness "
            "threshold in RDP-002 from 15 minutes "
            "to 5 minutes, which documents and "
            "systems need updating?"
        )
    )

    assert result.subject == (
        "rate-freshness threshold in RDP-002"
    )

    assert result.old_value is not None
    assert result.old_value.raw == "15 minutes"

    assert result.new_value is not None
    assert result.new_value.raw == "5 minutes"

    assert result.direction == "DECREASE"

    assert result.magnitude is not None
    assert round(result.magnitude, 3) == 0.667

    assert result.change_type == "VALUE_CHANGE"

    assert (
        "rate-freshness threshold in RDP-002"
        in result.concepts
    )


def test_authentication_replacement() -> None:
    engine = ChangeUnderstandingEngine()

    result = engine.analyze(
        (
            "If the CarrierConnect API changes "
            "authentication from Token v1 to "
            "JWT Bearer, which APIs, documentation, "
            "and workflows are affected?"
        )
    )

    assert result.subject == "authentication"

    assert result.old_value is not None
    assert result.old_value.raw == "Token v1"

    assert result.new_value is not None
    assert result.new_value.raw == "JWT Bearer"

    assert result.direction == "CHANGE"


def test_sla_change() -> None:
    engine = ChangeUnderstandingEngine()

    result = engine.analyze(
        (
            "Change the SLA resolution window "
            "from 4 hours to 1 hour for Tier-1 "
            "outage incidents in customer "
            "enterprise contracts."
        )
    )

    assert result.subject == (
        "SLA resolution window"
    )

    assert result.old_value is not None
    assert result.old_value.raw == "4 hours"

    assert result.new_value is not None
    assert result.new_value.raw == "1 hour"

    assert result.direction == "DECREASE"

    assert result.magnitude is not None
    assert round(result.magnitude, 3) == 0.75


def test_arrow_change() -> None:
    engine = ChangeUnderstandingEngine()

    result = engine.analyze(
        "RDP-002 rate threshold: 15m → 5m"
    )

    assert result.old_value is not None
    assert result.old_value.raw == "15m"

    assert result.new_value is not None
    assert result.new_value.raw == "5m"

    assert result.direction == "DECREASE"


def test_unstructured_requirement_is_supported() -> None:
    engine = ChangeUnderstandingEngine()

    result = engine.analyze(
        (
            "Introduce mandatory authentication "
            "for CarrierConnect integrations."
        )
    )

    assert result.change_type == (
        "REQUIREMENT_CHANGE"
    )

    assert result.old_value is None
    assert result.new_value is None

    assert result.direction == "CHANGE"

    assert len(result.concepts) > 0