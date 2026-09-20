from types import SimpleNamespace

from app.engines.relationship_extraction_engine import (
    RelationshipExtractionEngine,
)


def _entity(entity_id: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=entity_id,
        name=name,
    )


def test_extracts_calls_relationship() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "CustomerPortal",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "RateEngine API",
    )

    relationships = engine.extract(
        entities=[source, target],
        text=(
            "CustomerPortal calls RateEngine API "
            "to obtain a quote."
        ),
    )

    assert len(relationships) == 1
    assert relationships[0].relationship_type == "CALLS"
    assert relationships[0].source_entity_id == str(source.id)
    assert relationships[0].target_entity_id == str(target.id)


def test_extracts_reads_relationship() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "RateEngine",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "BillingCore",
    )

    relationships = engine.extract(
        entities=[source, target],
        text=(
            "RateEngine reads BillingCore "
            "for the current rate ledger."
        ),
    )

    assert len(relationships) == 1
    assert relationships[0].relationship_type == "READS_FROM"


def test_extracts_routes_to_relationship() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "RATE-409",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "Pricing & Rates",
    )

    relationships = engine.extract(
        entities=[source, target],
        text=(
            "A RATE-409 held quote routes to "
            "Pricing & Rates for resolution."
        ),
    )

    assert len(relationships) == 1
    assert relationships[0].relationship_type == "ROUTES_TO"


def test_extracts_structured_related_systems() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "RateEngine",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "BillingCore",
    )

    relationships = engine.extract(
        entities=[source, target],
        text="Related Systems: RateEngine, BillingCore",
    )

    assert len(relationships) == 1
    assert (
        relationships[0].relationship_type
        == "RELATED_SYSTEM"
    )


def test_extracts_ownership_relationship() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "RateEngine",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "Pricing & Rates",
    )

    relationships = engine.extract(
        entities=[source, target],
        text=(
            "RateEngine business logic is owned by "
            "Pricing & Rates."
        ),
    )

    assert len(relationships) == 1
    assert relationships[0].relationship_type == "OWNED_BY"


def test_does_not_create_relationship_without_trigger() -> None:
    engine = RelationshipExtractionEngine()

    source = _entity(
        "11111111-1111-1111-1111-111111111111",
        "RateEngine",
    )
    target = _entity(
        "22222222-2222-2222-2222-222222222222",
        "BillingCore",
    )

    relationships = engine.extract(
        entities=[source, target],
        text=(
            "RateEngine and BillingCore "
            "are both important systems."
        ),
    )

    assert relationships == []