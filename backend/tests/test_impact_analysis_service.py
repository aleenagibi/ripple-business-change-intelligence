from app.engines.change_understanding_engine import (
    ChangeSpecification,
    ChangeValue,
)


def test_change_specification_retrieval_query_includes_change_concepts() -> None:
    specification = ChangeSpecification(
        raw_query=(
            "Change rate freshness threshold "
            "from 15 minutes to 5 minutes"
        ),
        subject="rate freshness threshold",
        old_value=ChangeValue(
            raw="15 minutes",
            numeric_value=15.0,
            unit="minutes",
            normalized_value=900.0,
            dimension="duration",
        ),
        new_value=ChangeValue(
            raw="5 minutes",
            numeric_value=5.0,
            unit="minutes",
            normalized_value=300.0,
            dimension="duration",
        ),
        change_type="VALUE_CHANGE",
        direction="DECREASE",
        magnitude=0.6667,
        concepts=(
            "rate freshness threshold",
            "Change",
            "rate",
            "freshness",
            "threshold",
            "15",
            "minutes",
        ),
        evidence="15 minutes → 5 minutes",
    )

    result = specification.retrieval_query

    assert specification.raw_query in result
    assert "Business subject: rate freshness threshold" in result
    assert "Existing state: 15 minutes" in result
    assert "Proposed state: 5 minutes" in result
    assert "Business concepts:" in result
    assert "rate freshness threshold" in result


def test_change_specification_retrieval_query_preserves_original_query() -> None:
    specification = ChangeSpecification(
        raw_query="Replace legacy authentication with JWT Bearer",
        subject="legacy authentication",
        old_value=ChangeValue(
            raw="legacy authentication",
            numeric_value=None,
            unit=None,
            normalized_value=None,
            dimension=None,
        ),
        new_value=ChangeValue(
            raw="JWT Bearer",
            numeric_value=None,
            unit=None,
            normalized_value=None,
            dimension=None,
        ),
        change_type="REPLACEMENT",
        direction="REPLACEMENT",
        magnitude=None,
        concepts=(
            "legacy authentication",
            "Replace",
            "legacy",
            "authentication",
            "JWT",
            "Bearer",
        ),
        evidence="legacy authentication → JWT Bearer",
    )

    result = specification.retrieval_query

    assert result.startswith(
        "Replace legacy authentication with JWT Bearer"
    )
    assert "Business subject: legacy authentication" in result
    assert "Existing state: legacy authentication" in result
    assert "Proposed state: JWT Bearer" in result