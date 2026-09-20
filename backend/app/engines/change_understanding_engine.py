from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ChangeType = Literal[
    "VALUE_CHANGE",
    "REPLACEMENT",
    "ADDITION",
    "REMOVAL",
    "REQUIREMENT_CHANGE",
]

ChangeDirection = Literal[
    "INCREASE",
    "DECREASE",
    "REPLACEMENT",
    "ADDITION",
    "REMOVAL",
    "CHANGE",
]


@dataclass(frozen=True)
class ChangeValue:
    """A parsed old or new requirement value."""

    raw: str
    numeric_value: float | None
    unit: str | None
    normalized_value: float | None
    dimension: str | None


@dataclass(frozen=True)
class ChangeSpecification:
    """
    Structured representation of a proposed business change.

    This object deliberately contains only deterministic,
    explainable information extracted from the requirement.
    """

    raw_query: str
    subject: str | None

    old_value: ChangeValue | None
    new_value: ChangeValue | None

    change_type: ChangeType
    direction: ChangeDirection

    magnitude: float | None

    concepts: tuple[str, ...]

    evidence: str | None

    @property
    def is_structured_change(self) -> bool:
        return (
            self.old_value is not None
            and self.new_value is not None
        )

    @property
    def retrieval_query(self) -> str:
        """
        Produce a normalized retrieval representation.

        The original requirement is preserved, while the
        extracted change semantics are explicitly surfaced
        to the retrieval layer.
        """

        parts = [self.raw_query.strip()]

        if self.subject:
            parts.append(
                f"Business subject: {self.subject}"
            )

        if self.old_value:
            parts.append(
                f"Existing state: {self.old_value.raw}"
            )

        if self.new_value:
            parts.append(
                f"Proposed state: {self.new_value.raw}"
            )

        if self.concepts:
            parts.append(
                "Business concepts: "
                + ", ".join(self.concepts)
            )

        return " | ".join(
            part for part in parts if part
        )


class ChangeUnderstandingEngine:
    """
    Deterministic business requirement change parser.

    Responsibilities:

    1. Detect whether the requirement contains a
       before/after change.
    2. Extract the changed subject.
    3. Extract old and new values.
    4. Determine direction.
    5. Calculate magnitude when numeric comparison
       is possible.
    6. Extract searchable business concepts.

    This engine intentionally does not use an LLM.
    """

    _FROM_TO_PATTERN = re.compile(
        r"""
        \b
        from
        \s+
        (?P<old>[^,.;\n]+?)
        \s+
        (?:to|→|->)
        \s+
        (?P<new>[^,.;\n]+?)
        (?=
            \s+
            (?:
                for
                | which
                | that
                | so
                | because
                | and
            )
            \b
            |
            [,.;\n]
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _REPLACE_PATTERN = re.compile(
        r"""
        \b
        replace
        \s+
        (?P<old>[^,.;\n]+?)
        \s+
        with
        \s+
        (?P<new>[^,.;\n]+?)
        (?=
            \s+
            (?:
                for
                | which
                | that
                | so
                | because
                | and
            )
            \b
            |
            [,.;\n]
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _ARROW_PATTERN = re.compile(
        r"""
        (?P<old>
            (?:
                \d+(?:\.\d+)?
                \s*
                (?:ms|milliseconds?|s|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?|%|percent)?
            )
            |
            [A-Za-z][A-Za-z0-9 _-]{1,40}
        )
        \s*
        (?:→|->)
        \s*
        (?P<new>
            (?:
                \d+(?:\.\d+)?
                \s*
                (?:ms|milliseconds?|s|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?|%|percent)?
            )
            |
            [A-Za-z][A-Za-z0-9 _-]{1,40}
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _SUBJECT_PATTERN = re.compile(
        r"""
        \b
        (?:
            change
            | changes
            | changed
            | update
            | updates
            | updated
            | replace
            | replaces
            | replaced
        )
        \s+
        (?:the\s+)?
        (?P<subject>.+?)
        \s+
        from
        \s+
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _REPLACEMENT_SUBJECT_PATTERN = re.compile(
        r"""
        \b
        replace
        \s+
        (?:the\s+)?
        (?P<subject>.+?)
        \s+
        with
        \s+
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _VALUE_PATTERN = re.compile(
        r"""
        ^
        \s*
        (?P<number>\d+(?:\.\d+)?)
        \s*
        (?P<unit>
            ms
            | milliseconds?
            | s
            | seconds?
            | m
            | mins?
            | minutes?
            | h
            | hrs?
            | hours?
            | d
            | days?
            | %
            | percent(?:age)?
        )?
        \s*
        $
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    _UNIT_DEFINITIONS = {
        "ms": ("duration", 0.001),
        "millisecond": ("duration", 0.001),
        "milliseconds": ("duration", 0.001),
        "s": ("duration", 1.0),
        "sec": ("duration", 1.0),
        "secs": ("duration", 1.0),
        "second": ("duration", 1.0),
        "seconds": ("duration", 1.0),
        "m": ("duration", 60.0),
        "min": ("duration", 60.0),
        "mins": ("duration", 60.0),
        "minute": ("duration", 60.0),
        "minutes": ("duration", 60.0),
        "h": ("duration", 3600.0),
        "hr": ("duration", 3600.0),
        "hrs": ("duration", 3600.0),
        "hour": ("duration", 3600.0),
        "hours": ("duration", 3600.0),
        "d": ("duration", 86400.0),
        "day": ("duration", 86400.0),
        "days": ("duration", 86400.0),
        "%": ("percentage", 1.0),
        "percent": ("percentage", 1.0),
        "percentage": ("percentage", 1.0),
    }

    _STOPWORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "from",
        "for",
        "in",
        "on",
        "with",
        "by",
        "this",
        "that",
        "which",
        "what",
        "will",
        "would",
        "should",
        "could",
        "change",
        "changes",
        "changed",
        "update",
        "updates",
        "updated",
        "replace",
        "replaces",
        "replaced",
        "need",
        "needs",
        "affected",
        "affect",
        "impact",
        "impacted",
        "documents",
        "systems",
        "apis",
        "api",
        "workflows",
        "policies",
    }

    def analyze(
        self,
        query: str,
    ) -> ChangeSpecification:
        """
        Convert a natural-language requirement into
        a deterministic change specification.
        """

        normalized_query = " ".join(
            query.strip().split()
        )

        if not normalized_query:
            raise ValueError(
                "Requirement query cannot be empty."
            )

        match = (
            self._FROM_TO_PATTERN.search(
                normalized_query
            )
        )

        change_type: ChangeType = (
            "VALUE_CHANGE"
        )

        if match is None:
            match = self._REPLACE_PATTERN.search(
                normalized_query
            )
            change_type = "REPLACEMENT"

        if match is None:
            match = self._ARROW_PATTERN.search(
                normalized_query
            )
            change_type = "VALUE_CHANGE"

        if match is None:
            return ChangeSpecification(
                raw_query=normalized_query,
                subject=self._extract_fallback_subject(
                    normalized_query
                ),
                old_value=None,
                new_value=None,
                change_type="REQUIREMENT_CHANGE",
                direction="CHANGE",
                magnitude=None,
                concepts=self._extract_concepts(
                    normalized_query,
                    None,
                ),
                evidence=None,
            )

        old_raw = self._clean_value(
            match.group("old")
        )

        new_raw = self._clean_value(
            match.group("new")
        )

        old_value = self._parse_value(
            old_raw
        )

        new_value = self._parse_value(
            new_raw
        )

        subject = self._extract_subject(
            normalized_query,
            match,
            change_type,
        )

        if change_type == "REPLACEMENT":
            direction: ChangeDirection = (
                "REPLACEMENT"
            )
            magnitude = None

        elif (
            old_value.numeric_value is not None
            and new_value.numeric_value is not None
            and self._compatible_dimensions(
                old_value,
                new_value,
            )
        ):
            direction, magnitude = (
                self._calculate_numeric_change(
                    old_value,
                    new_value,
                )
            )

        else:
            direction = "CHANGE"
            magnitude = None

        concepts = self._extract_concepts(
            normalized_query,
            subject,
        )

        evidence = (
            f"{old_value.raw} → "
            f"{new_value.raw}"
        )

        return ChangeSpecification(
            raw_query=normalized_query,
            subject=subject,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            direction=direction,
            magnitude=magnitude,
            concepts=concepts,
            evidence=evidence,
        )

    def _extract_subject(
        self,
        query: str,
        match: re.Match[str],
        change_type: ChangeType,
    ) -> str | None:
        if change_type == "REPLACEMENT":
            replacement_match = (
                self._REPLACEMENT_SUBJECT_PATTERN.search(
                    query
                )
            )

            if replacement_match:
                return self._clean_subject(
                    replacement_match.group(
                        "subject"
                    )
                )

        subject_match = (
            self._SUBJECT_PATTERN.search(query)
        )

        if subject_match:
            return self._clean_subject(
                subject_match.group("subject")
            )

        prefix = query[: match.start()].strip()

        prefix = re.sub(
            r"^(?:if|when|once|after)\s+",
            "",
            prefix,
            flags=re.IGNORECASE,
        )

        prefix = re.sub(
            r"\b(?:we|the system|users?)\s+",
            "",
            prefix,
            flags=re.IGNORECASE,
        )

        return self._clean_subject(prefix)

    def _extract_fallback_subject(
        self,
        query: str,
    ) -> str | None:
        cleaned = re.sub(
            r"^(?:if|when|please)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\b(?:which|what)\b.*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        return self._clean_subject(cleaned)

    def _clean_subject(
        self,
        subject: str,
    ) -> str | None:
        cleaned = subject.strip(
            " \t\n\r:,-"
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        )

        if not cleaned:
            return None

        return cleaned

    def _clean_value(
        self,
        value: str,
    ) -> str:
        cleaned = value.strip(
            " \t\n\r:,-"
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        )

        return cleaned

    def _parse_value(
        self,
        raw: str,
    ) -> ChangeValue:
        match = self._VALUE_PATTERN.match(
            raw
        )

        if match is None:
            return ChangeValue(
                raw=raw,
                numeric_value=None,
                unit=None,
                normalized_value=None,
                dimension=None,
            )

        numeric_value = float(
            match.group("number")
        )

        unit = match.group("unit")

        if unit is None:
            return ChangeValue(
                raw=raw,
                numeric_value=numeric_value,
                unit=None,
                normalized_value=numeric_value,
                dimension="unitless",
            )

        normalized_unit = unit.lower()

        dimension, multiplier = (
            self._UNIT_DEFINITIONS[
                normalized_unit
            ]
        )

        return ChangeValue(
            raw=raw,
            numeric_value=numeric_value,
            unit=normalized_unit,
            normalized_value=(
                numeric_value * multiplier
            ),
            dimension=dimension,
        )

    @staticmethod
    def _compatible_dimensions(
        old_value: ChangeValue,
        new_value: ChangeValue,
    ) -> bool:
        return (
            old_value.dimension is not None
            and new_value.dimension is not None
            and old_value.dimension
            == new_value.dimension
        )

    @staticmethod
    def _calculate_numeric_change(
        old_value: ChangeValue,
        new_value: ChangeValue,
    ) -> tuple[ChangeDirection, float | None]:
        old_normalized = (
            old_value.normalized_value
        )
        new_normalized = (
            new_value.normalized_value
        )

        if (
            old_normalized is None
            or new_normalized is None
        ):
            return "CHANGE", None

        if new_normalized > old_normalized:
            direction: ChangeDirection = (
                "INCREASE"
            )
        elif new_normalized < old_normalized:
            direction = "DECREASE"
        else:
            direction = "CHANGE"

        if old_normalized == 0:
            magnitude = None
        else:
            magnitude = abs(
                new_normalized
                - old_normalized
            ) / abs(old_normalized)

        return direction, magnitude

    def _extract_concepts(
        self,
        query: str,
        subject: str | None,
    ) -> tuple[str, ...]:
        concepts: list[str] = []

        if subject:
            concepts.append(subject)

        candidates = re.findall(
            r"[A-Za-z][A-Za-z0-9_-]{2,}",
            query,
        )

        for candidate in candidates:
            normalized = candidate.strip(
                "_-"
            )

            if not normalized:
                continue

            if (
                normalized.lower()
                in self._STOPWORDS
            ):
                continue

            if normalized not in concepts:
                concepts.append(normalized)

        return tuple(concepts[:20])