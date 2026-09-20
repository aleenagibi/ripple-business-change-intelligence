from types import SimpleNamespace

from app.engines.canonical_reconciliation_engine import (
    CanonicalReconciliationEngine,
    ReconciliationRelation,
)


def make_entity(
    entity_id: str,
    name: str,
    entity_type: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entity_id,
        name=name,
        normalized_name=name.lower(),
        entity_type=entity_type,
    )


def test_token_similarity_identical_names() -> None:
    similarity = (
        CanonicalReconciliationEngine._token_similarity(
            "payment processing",
            "payment processing",
        )
    )

    assert similarity == 1.0


def test_token_similarity_unrelated_names() -> None:
    similarity = (
        CanonicalReconciliationEngine._token_similarity(
            "payment processing",
            "customer database",
        )
    )

    assert similarity == 0.0


def test_descriptive_extension_is_detected() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment processing",
            "successful payment processing",
        )
    )

    assert (
        relationship
        == ReconciliationRelation.DESCRIPTIVE_EXTENSION
    )


def test_context_extension_is_detected() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment failures",
            "checkout payment failures",
        )
    )

    assert (
        relationship
        == ReconciliationRelation.CONTEXT_EXTENSION
    )


def test_rules_are_context_extension() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment processing",
            "payment processing rules",
        )
    )

    assert (
        relationship
        == ReconciliationRelation.CONTEXT_EXTENSION
    )


def test_unrelated_names_are_structural_mismatch() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment processing",
            "customer database",
        )
    )

    assert (
        relationship
        == ReconciliationRelation.STRUCTURAL_MISMATCH
    )


def test_structural_similarity_for_descriptive_extension() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment processing",
            "successful payment processing",
        )
    )

    similarity = (
        CanonicalReconciliationEngine._structural_similarity(
            "payment processing",
            "successful payment processing",
            relationship,
        )
    )

    assert similarity == 0.90


def test_structural_similarity_for_context_extension() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "payment failures",
            "checkout payment failures",
        )
    )

    similarity = (
        CanonicalReconciliationEngine._structural_similarity(
            "payment failures",
            "checkout payment failures",
            relationship,
        )
    )

    assert similarity == 0.20


def test_context_extension_requires_stronger_evidence() -> None:
    result = (
        CanonicalReconciliationEngine._passes_threshold(
            combined_similarity=0.90,
            dense_similarity=0.92,
            relationship=(
                ReconciliationRelation.CONTEXT_EXTENSION
            ),
        )
    )

    assert result is False


def test_context_extension_can_pass_at_very_high_similarity() -> None:
    result = (
        CanonicalReconciliationEngine._passes_threshold(
            combined_similarity=0.88,
            dense_similarity=0.95,
            relationship=(
                ReconciliationRelation.CONTEXT_EXTENSION
            ),
        )
    )

    assert result is True


def test_context_extension_never_gets_high_confidence() -> None:
    confidence = (
        CanonicalReconciliationEngine._calculate_confidence(
            combined_similarity=0.97,
            dense_similarity=0.98,
            relationship=(
                ReconciliationRelation.CONTEXT_EXTENSION
            ),
        )
    )

    assert confidence == "REVIEW"


def test_descriptive_extension_can_get_high_confidence() -> None:
    confidence = (
        CanonicalReconciliationEngine._calculate_confidence(
            combined_similarity=0.91,
            dense_similarity=0.95,
            relationship=(
                ReconciliationRelation.DESCRIPTIVE_EXTENSION
            ),
        )
    )

    assert confidence == "HIGH"


def test_grouping_by_entity_type() -> None:
    entities = [
        make_entity(
            "1",
            "Payment processing",
            "BUSINESS_CONCEPT",
        ),
        make_entity(
            "2",
            "Payment API",
            "API",
        ),
        make_entity(
            "3",
            "Payment processing rules",
            "BUSINESS_CONCEPT",
        ),
    ]

    grouped = (
        CanonicalReconciliationEngine._group_by_entity_type(
            entities
        )
    )

    assert set(grouped) == {
        "BUSINESS_CONCEPT",
        "API",
    }

    assert len(
        grouped["BUSINESS_CONCEPT"]
    ) == 2

    assert len(
        grouped["API"]
    ) == 1


def test_invalid_entities_are_filtered() -> None:
    entities = [
        make_entity(
            "1",
            "Payment processing",
            "BUSINESS_CONCEPT",
        ),
        SimpleNamespace(
            id=None,
            name="Invalid",
            normalized_name="invalid",
            entity_type="BUSINESS_CONCEPT",
        ),
        SimpleNamespace(
            id="3",
            name="",
            normalized_name="",
            entity_type="BUSINESS_CONCEPT",
        ),
    ]

    valid = (
        CanonicalReconciliationEngine._filter_valid_entities(
            entities
        )
    )

    assert len(valid) == 1
    assert valid[0].name == "Payment processing"


def test_threshold_validation() -> None:
    try:
        CanonicalReconciliationEngine(
            threshold=1.2
        )
    except ValueError as exc:
        assert "between 0 and 1" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_high_confidence_threshold_validation() -> None:
    try:
        CanonicalReconciliationEngine(
            threshold=0.90,
            high_confidence_threshold=0.80,
        )
    except ValueError as exc:
        assert (
            "greater than or equal"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_repeated_name_artifact_has_high_structural_similarity() -> None:
    relationship = (
        CanonicalReconciliationEngine._classify_relationship(
            "checkout workflow",
            "checkout workflow the checkout workflow",
        )
    )

    similarity = (
        CanonicalReconciliationEngine._structural_similarity(
            "checkout workflow",
            "checkout workflow the checkout workflow",
            relationship,
        )
    )

    assert (
        relationship
        == ReconciliationRelation.REPEATED_NAME_ARTIFACT
    )

    assert similarity == 1.0