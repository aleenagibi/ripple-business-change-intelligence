from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import spacy

from app.models.entity import BusinessEntity


@dataclass(frozen=True)
class ExtractedRelationship:
    """A relationship discovered between two business entities."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float
    evidence: str


class RelationshipExtractionEngine:
    """
    Extract explicit, evidence-backed relationships between known entities.

    Ripple uses the relationship graph for impact propagation, so this engine
    deliberately avoids creating a relationship merely because two entities
    occur in the same sentence.

    A relationship is created only when:
      1. both entities are explicitly mentioned,
      2. a controlled relationship trigger occurs between them, and
      3. the source/target pair is the closest valid pair around that trigger.

    This prevents a sentence containing many entities from becoming a
    fully-connected graph.
    """

    # Ordered longest-first during extraction. The patterns are intentionally
    # explicit: Ripple should prefer precision over speculative graph edges.
    RELATIONSHIP_TRIGGERS: tuple[tuple[str, str, str, float], ...] = (
        # System / API interaction
        (r"\bcalls?\b", "CALLS", "FORWARD", 0.96),
        (r"\binvokes?\b", "CALLS", "FORWARD", 0.96),
        (r"\brequests?\b", "CALLS", "FORWARD", 0.94),
        (r"\bqueries?\b", "QUERIES", "FORWARD", 0.94),
        (r"\breads?\s+from\b", "READS_FROM", "FORWARD", 0.96),
        (r"\breads?\s+from\b", "READS_FROM", "FORWARD", 0.96),
        (r"\breads?\b", "READS_FROM", "FORWARD", 0.94),
        (r"\bfetch(?:es)?\s+from\b", "READS_FROM", "FORWARD", 0.94),
        (r"\bwrites?\s+to\b", "WRITES_TO", "FORWARD", 0.96),
        (r"\bsends?\s+to\b", "SENDS_TO", "FORWARD", 0.94),
        (r"\bposts?\s+to\b", "SENDS_TO", "FORWARD", 0.94),

        # General dependency / usage
        (r"\bdepends\s+on\b", "DEPENDS_ON", "FORWARD", 0.96),
        (r"\bdepend\s+on\b", "DEPENDS_ON", "FORWARD", 0.96),
        (r"\brelies\s+on\b", "DEPENDS_ON", "FORWARD", 0.96),
        (r"\brely\s+on\b", "DEPENDS_ON", "FORWARD", 0.96),
        (r"\buses?\b", "USES", "FORWARD", 0.93),
        (r"\butilizes?\b", "USES", "FORWARD", 0.93),
        (r"\bleverages?\b", "USES", "FORWARD", 0.93),

        # Workflow / event flow
        (r"\broutes?\s+to\b", "ROUTES_TO", "FORWARD", 0.96),
        (r"\bsends?\s+to\b", "ROUTES_TO", "FORWARD", 0.92),
        (r"\btriggers?\b", "TRIGGERS", "FORWARD", 0.96),
        (r"\binitiates?\b", "TRIGGERS", "FORWARD", 0.94),
        (r"\bfeeds?\b", "FEEDS", "FORWARD", 0.92),
        (r"\bnotifies?\b", "NOTIFIES", "FORWARD", 0.96),
        (r"\balerts?\b", "NOTIFIES", "FORWARD", 0.94),
        (r"\bloops?\s+in\b", "INVOLVES", "FORWARD", 0.92),

        # Ownership / responsibility
        (r"\bowned\s+by\b", "OWNED_BY", "FORWARD", 0.98),
        (r"\bmaintained\s+by\b", "MAINTAINED_BY", "FORWARD", 0.98),
        (r"\boperated\s+by\b", "OPERATED_BY", "FORWARD", 0.98),
        (r"\bmanaged\s+by\b", "MANAGED_BY", "FORWARD", 0.96),
        (r"\bassigned\s+to\b", "ASSIGNED_TO", "FORWARD", 0.96),
        (r"\bescalated\s+to\b", "ESCALATES_TO", "FORWARD", 0.96),
        (r"\bcoordinates?\s+with\b", "COORDINATES_WITH", "FORWARD", 0.94),

        # Governance / implementation
        (r"\bgoverned\s+by\b", "GOVERNED_BY", "FORWARD", 0.98),
        (r"\bregulated\s+by\b", "GOVERNED_BY", "FORWARD", 0.96),
        (r"\benforced\s+by\b", "ENFORCED_BY", "FORWARD", 0.98),
        (r"\bimplemented\s+by\b", "IMPLEMENTED_BY", "FORWARD", 0.96),
        (r"\bimplements?\b", "IMPLEMENTS", "FORWARD", 0.94),
        (r"\bsupports?\b", "SUPPORTS", "FORWARD", 0.90),

        # Documentation / traceability
        (r"\breferences?\b", "REFERENCES", "FORWARD", 0.98),
        (r"\bdescribed\s+in\b", "DOCUMENTED_IN", "FORWARD", 0.96),
        (r"\bdocumented\s+in\b", "DOCUMENTED_IN", "FORWARD", 0.96),
        (r"\bdefined\s+in\b", "DEFINED_IN", "FORWARD", 0.96),
        (r"\bspecified\s+in\b", "DEFINED_IN", "FORWARD", 0.96),
        (r"\brelated\s+to\b", "RELATED_TO", "FORWARD", 0.86),
    )

    # Structured document metadata is useful only when a source entity is
    # explicitly present on the same line. We never turn a list of N entities
    # into N^2 relationships.
    STRUCTURED_RELATIONSHIP_LABELS: tuple[tuple[str, str, float], ...] = (
        ("related system", "RELATED_SYSTEM", 0.90),
        ("related systems", "RELATED_SYSTEM", 0.90),
        ("related api", "RELATED_API", 0.90),
        ("related apis", "RELATED_API", 0.90),
        ("related workflow", "RELATED_WORKFLOW", 0.90),
        ("related workflows", "RELATED_WORKFLOW", 0.90),
        ("related policy", "RELATED_POLICY", 0.90),
        ("related policies", "RELATED_POLICY", 0.90),
        ("related sop", "RELATED_SOP", 0.90),
        ("related sops", "RELATED_SOP", 0.90),
        ("related document", "REFERENCES", 0.90),
        ("related documents", "REFERENCES", 0.90),
    )

    MAX_TRIGGER_ENTITY_DISTANCE = 240
    MAX_STRUCTURED_LINE_LENGTH = 600

    def __init__(self) -> None:
        self.nlp = spacy.load("en_core_web_sm")

    def extract(
        self,
        entities: list[BusinessEntity],
        text: str,
    ) -> list[ExtractedRelationship]:
        """Extract precise relationships from a document chunk."""

        if not text.strip() or len(entities) < 2:
            return []

        doc = self.nlp(text)

        relationships: dict[
            tuple[str, str, str],
            ExtractedRelationship,
        ] = {}

        self._extract_explicit_relationships(
            doc=doc,
            entities=entities,
            relationships=relationships,
        )

        self._extract_structured_relationships(
            doc=doc,
            entities=entities,
            relationships=relationships,
        )

        return list(relationships.values())

    def _extract_explicit_relationships(
        self,
        doc: Any,
        entities: list[BusinessEntity],
        relationships: dict[
            tuple[str, str, str],
            ExtractedRelationship,
        ],
    ) -> None:
        """
        Extract one nearest source/target pair per trigger occurrence.

        The previous implementation considered every ordered pair of
        mentions in a sentence. That causes sentences with several entities
        to produce false relationships. Here each trigger gets only the
        closest valid entity before and after it.
        """

        for sentence in doc.sents:
            mentions = self._find_entity_mentions(
                sentence=sentence,
                entities=entities,
            )

            if len(mentions) < 2:
                continue

            sentence_text = sentence.text

            for (
                pattern,
                relationship_type,
                _direction,
                confidence,
            ) in self.RELATIONSHIP_TRIGGERS:
                for match in re.finditer(
                    pattern,
                    sentence_text,
                    flags=re.IGNORECASE,
                ):
                    source = self._nearest_mention_before(
                        mentions=mentions,
                        position=match.start(),
                    )
                    target = self._nearest_mention_after(
                        mentions=mentions,
                        position=match.end(),
                    )

                    if source is None or target is None:
                        continue

                    source_distance = (
                        match.start() - source["end"]
                    )
                    target_distance = (
                        target["start"] - match.end()
                    )

                    if (
                        source_distance
                        > self.MAX_TRIGGER_ENTITY_DISTANCE
                        or target_distance
                        > self.MAX_TRIGGER_ENTITY_DISTANCE
                    ):
                        continue

                    if source["entity"].id == target["entity"].id:
                        continue

                    evidence = sentence_text.strip()

                    self._add_relationship(
                        relationships=relationships,
                        source=source["entity"],
                        target=target["entity"],
                        relationship_type=relationship_type,
                        confidence=confidence,
                        evidence=evidence,
                    )

    def _extract_structured_relationships(
        self,
        doc: Any,
        entities: list[BusinessEntity],
        relationships: dict[
            tuple[str, str, str],
            ExtractedRelationship,
        ],
    ) -> None:
        """
        Extract relationships from explicit metadata lines.

        Supported forms include:

            Related System: RateEngine
            Related Systems: RateEngine, BillingCore

        For a list-only field, relationships are created only between the
        entities explicitly listed in that field. This does not connect
        unrelated entities elsewhere in the chunk.
        """

        for line in self._iter_lines(doc.text):
            if len(line) > self.MAX_STRUCTURED_LINE_LENGTH:
                continue

            normalized_line = self._normalize(line)

            for label, relationship_type, confidence in (
                self.STRUCTURED_RELATIONSHIP_LABELS
            ):
                label_match = re.search(
                    rf"\b{re.escape(label)}\s*:",
                    normalized_line,
                    flags=re.IGNORECASE,
                )

                if label_match is None:
                    continue

                line_mentions = self._find_entity_mentions_in_text(
                    text=line,
                    entities=entities,
                )

                if len(line_mentions) < 2:
                    continue

                label_position = label_match.start()

                # Case 1:
                # "Some Source: Related Systems: Target"
                # The nearest entity before the field label is the source.
                source_candidates = [
                    mention
                    for mention in line_mentions
                    if mention["end"] <= label_position
                ]

                target_candidates = [
                    mention
                    for mention in line_mentions
                    if mention["start"] >= label_match.end()
                ]

                if source_candidates and target_candidates:
                    source = max(
                        source_candidates,
                        key=lambda mention: mention["end"],
                    )

                    for target in target_candidates:
                        if source["entity"].id == target["entity"].id:
                            continue

                        self._add_relationship(
                            relationships=relationships,
                            source=source["entity"],
                            target=target["entity"],
                            relationship_type=relationship_type,
                            confidence=confidence,
                            evidence=line.strip(),
                        )

                    continue

                # Case 2:
                # "Related Systems: RateEngine, BillingCore"
                # The field itself is the source of the relationship.
                # Connect only explicitly listed entities.
                listed_entities = [
                    mention["entity"]
                    for mention in line_mentions
                    if mention["start"] >= label_match.end()
                ]

                for index, source in enumerate(listed_entities):
                    for target in listed_entities[index + 1:]:
                        if source.id == target.id:
                            continue

                        self._add_relationship(
                            relationships=relationships,
                            source=source,
                            target=target,
                            relationship_type=relationship_type,
                            confidence=confidence,
                            evidence=line.strip(),
                        )

                        # Keep the structured relation directional and
                        # deterministic rather than creating a clique.
                        break

    def _find_entity_mentions(
        self,
        sentence: Any,
        entities: list[BusinessEntity],
    ) -> list[dict[str, Any]]:
        """Find non-overlapping entity mentions inside one spaCy sentence."""

        return self._find_entity_mentions_in_text(
            text=sentence.text,
            entities=entities,
        )

    def _find_entity_mentions_in_text(
        self,
        text: str,
        entities: list[BusinessEntity],
    ) -> list[dict[str, Any]]:
        """Find entity names using normalized character positions."""

        normalized_text = self._normalize(text)

        if not normalized_text:
            return []

        mentions: list[dict[str, Any]] = []

        for entity in entities:
            normalized_name = self._normalize(
                str(entity.name),
            )

            if not normalized_name:
                continue

            search_start = 0

            while search_start < len(normalized_text):
                position = normalized_text.find(
                    normalized_name,
                    search_start,
                )

                if position == -1:
                    break

                end = position + len(normalized_name)

                if self._is_word_boundary(
                    normalized_text,
                    position,
                    end,
                ):
                    mentions.append(
                        {
                            "entity": entity,
                            "start": position,
                            "end": end,
                        }
                    )

                search_start = end

        mentions.sort(
            key=lambda mention: (
                mention["start"],
                -(
                    mention["end"]
                    - mention["start"]
                ),
            )
        )

        return self._remove_overlapping_mentions(
            mentions,
        )

    @staticmethod
    def _nearest_mention_before(
        mentions: list[dict[str, Any]],
        position: int,
    ) -> dict[str, Any] | None:
        """Return the closest entity ending before the trigger."""

        candidates = [
            mention
            for mention in mentions
            if mention["end"] <= position
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda mention: mention["end"],
        )

    @staticmethod
    def _nearest_mention_after(
        mentions: list[dict[str, Any]],
        position: int,
    ) -> dict[str, Any] | None:
        """Return the closest entity starting after the trigger."""

        candidates = [
            mention
            for mention in mentions
            if mention["start"] >= position
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda mention: mention["start"],
        )

    @staticmethod
    def _remove_overlapping_mentions(
        mentions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Keep the longest mention when entity spans overlap."""

        accepted: list[dict[str, Any]] = []

        for mention in mentions:
            overlaps = any(
                mention["start"] < existing["end"]
                and mention["end"] > existing["start"]
                for existing in accepted
            )

            if not overlaps:
                accepted.append(mention)

        return accepted

    @staticmethod
    def _is_word_boundary(
        text: str,
        start: int,
        end: int,
    ) -> bool:
        """Prevent matching an entity inside a larger alphanumeric token."""

        before_is_word = (
            start > 0
            and (
                text[start - 1].isalnum()
                or text[start - 1] == "_"
            )
        )

        after_is_word = (
            end < len(text)
            and (
                text[end].isalnum()
                or text[end] == "_"
            )
        )

        return not before_is_word and not after_is_word

    @staticmethod
    def _add_relationship(
        relationships: dict[
            tuple[str, str, str],
            ExtractedRelationship,
        ],
        source: BusinessEntity,
        target: BusinessEntity,
        relationship_type: str,
        confidence: float,
        evidence: str,
    ) -> None:
        """Add or strengthen one evidence-backed relationship."""

        if source.id == target.id:
            return

        key = (
            str(source.id),
            str(target.id),
            relationship_type,
        )

        candidate = ExtractedRelationship(
            source_entity_id=str(source.id),
            target_entity_id=str(target.id),
            relationship_type=relationship_type,
            confidence=float(confidence),
            evidence=evidence.strip(),
        )

        existing = relationships.get(key)

        if (
            existing is None
            or candidate.confidence > existing.confidence
        ):
            relationships[key] = candidate

    @staticmethod
    def _iter_lines(text: str) -> list[str]:
        """Yield meaningful non-empty lines from a chunk."""

        return [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize whitespace without destroying character positions."""

        return re.sub(
            r"\s+",
            " ",
            value.strip(),
        )
