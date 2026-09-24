from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

import spacy
from spacy.tokens import Doc, Span, Token


@dataclass(frozen=True)
class ExtractedEntity:
    """Result produced by the entity extraction engine."""

    name: str
    normalized_name: str
    entity_type: str
    description: str | None = None


class EntityExtractionEngine:
    """
    General-purpose entity extraction engine for Ripple.

    The engine discovers entities from the document itself rather than
    maintaining organization-specific business vocabularies.

    Supported entity categories:

        BUSINESS_CONCEPT
        TECHNOLOGY
        SYSTEM
        API
        WORKFLOW
        POLICY
        TEAM
        DOCUMENTATION
        PROJECT
        ORGANIZATION

    Extraction strategy:

        document
            ↓
        sentence segmentation
            ↓
        structural artifact detection
            ↓
        spaCy named entities
            ↓
        noun-phrase candidates
            ↓
        candidate validation
            ↓
        overlap resolution
            ↓
        normalized-name reconciliation
            ↓
        final entities
    """

    # ------------------------------------------------------------------
    # Supported Ripple entity types
    # ------------------------------------------------------------------

    ENTITY_TYPES = frozenset(
        {
            "BUSINESS_CONCEPT",
            "TECHNOLOGY",
            "SYSTEM",
            "API",
            "WORKFLOW",
            "POLICY",
            "TEAM",
            "DOCUMENTATION",
            "PROJECT",
            "ORGANIZATION",
        }
    )

    # ------------------------------------------------------------------
    # Generic structural vocabulary.
    #
    # These words describe the KIND of artifact.
    # They are not organization-specific business vocabulary.
    # ------------------------------------------------------------------

    STRUCTURAL_MARKERS: dict[str, frozenset[str]] = {
        "API": frozenset(
            {
                "api",
                "sdk",
            }
        ),
        "WORKFLOW": frozenset(
            {
                "workflow",
                "pipeline",
                "procedure",
            }
        ),
        "POLICY": frozenset(
            {
                "policy",
                "regulation",
                "standard",
                "guideline",
            }
        ),
        "TEAM": frozenset(
            {
                "team",
                "department",
                "committee",
                "squad",
            }
        ),
        "DOCUMENTATION": frozenset(
            {
                "documentation",
                "manual",
                "guide",
            }
        ),
        "PROJECT": frozenset(
            {
                "project",
                "initiative",
                "program",
            }
        ),
        "SYSTEM": frozenset(
            {
                "system",
                "platform",
                "application",
                "database",
                "service",
                "engine",
            }
        ),
    }

    STRUCTURAL_WORDS = frozenset(
        word
        for markers in STRUCTURAL_MARKERS.values()
        for word in markers
    )

    # ------------------------------------------------------------------
    # Grammatical words.
    # ------------------------------------------------------------------

    FUNCTION_WORDS = frozenset(
        {
            "the",
            "a",
            "an",
            "this",
            "that",
            "these",
            "those",
            "our",
            "your",
            "their",
            "its",
            "my",
            "his",
            "her",
            "which",
            "what",
            "whose",
        }
    )

    # ------------------------------------------------------------------
    # Generic words that have very little entity value on their own.
    #
    # These are linguistic stop concepts, NOT Ripple-domain vocabulary.
    # ------------------------------------------------------------------

    GENERIC_WORDS = frozenset(
        {
            "thing",
            "something",
            "anything",
            "everything",
            "nothing",
            "example",
            "way",
            "time",
            "part",
            "kind",
            "type",
            "number",
            "person",
            "people",
            "item",
            "case",
            "area",
            "aspect",
            "fact",
            "result",
            "detail",
            "details",
            "content",
        }
    )

    # ------------------------------------------------------------------
    # API / endpoint patterns.
    # ------------------------------------------------------------------

    API_PATTERN = re.compile(
        r"""
        (?:
            \b[A-Za-z][A-Za-z0-9_-]*(?:API|SDK)\b
            |
            \b(?:GET|POST|PUT|PATCH|DELETE)
            \s+
            /
            [A-Za-z0-9_./{}:-]+
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # ------------------------------------------------------------------
    # Type precedence.
    #
    # A structural artifact is more specific than a generic
    # BUSINESS_CONCEPT classification.
    # ------------------------------------------------------------------

    TYPE_PRIORITY = {
        "API": 100,
        "WORKFLOW": 90,
        "POLICY": 80,
        "TEAM": 70,
        "DOCUMENTATION": 60,
        "SYSTEM": 50,
        "PROJECT": 40,
        "ORGANIZATION": 30,
        "TECHNOLOGY": 20,
        "BUSINESS_CONCEPT": 10,
    }

    # ==================================================================
    # INITIALIZATION
    # ==================================================================

    def __init__(self) -> None:
        self.nlp = spacy.load("en_core_web_sm")

        # Guarantee sentence boundaries even if the installed spaCy
        # pipeline does not provide them.
        if not self.nlp.has_pipe("parser"):
            if not self.nlp.has_pipe("senter"):
                self.nlp.add_pipe(
                    "sentencizer",
                    first=True,
                )

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    def extract(
        self,
        text: str,
    ) -> list[ExtractedEntity]:
        """
        Extract entities from a document/chunk.

        This is the public contract consumed by EntityService.
        """

        if not text or not text.strip():
            return []

        doc = self.nlp(text)

        candidates: list[
            tuple[Span, str | None, float]
        ] = []

        candidates.extend(
            self._extract_api_patterns(doc)
        )

        candidates.extend(
            self._extract_named_entities(doc)
        )

        candidates.extend(
            self._extract_structural_phrases(doc)
        )

        candidates.extend(
            self._extract_business_phrases(doc)
        )

        candidates = self._clean_candidates(
            candidates
        )

        candidates = self._filter_candidates(
            candidates
        )

        candidates = self._resolve_overlaps(
            candidates
        )

        return self._reconcile_entities(
            candidates
        )

    # ==================================================================
    # CANDIDATE EXTRACTION
    # ==================================================================

    def _extract_api_patterns(
        self,
        doc: Doc,
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        results: list[
            tuple[Span, str | None, float]
        ] = []

        for match in self.API_PATTERN.finditer(
            doc.text
        ):
            span = doc.char_span(
                match.start(),
                match.end(),
                alignment_mode="expand",
            )

            if span is None:
                continue

            results.append(
                (
                    span,
                    "API_PATTERN",
                    1.00,
                )
            )

        return results

    def _extract_named_entities(
        self,
        doc: Doc,
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        results: list[
            tuple[Span, str | None, float]
        ] = []

        for span in doc.ents:
            if not span.text.strip():
                continue

            if len(span) == 1:
                if not self._valid_single_token(
                    span[0],
                    span.label_,
                ):
                    continue

            results.append(
                (
                    span,
                    span.label_,
                    self._ner_score(span),
                )
            )

        return results

    def _extract_structural_phrases(
        self,
        doc: Doc,
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        """
        Extract artifact phrases around structural markers.

        Examples of the general pattern:

            <noun phrase> API
            <noun phrase> database
            <noun phrase> workflow
            <noun phrase> policy
            <noun phrase> team
            <noun phrase> service

        The business part is discovered from the document.
        """

        results: list[
            tuple[Span, str | None, float]
        ] = []

        for sentence in doc.sents:
            sentence_tokens = list(sentence)

            for index, token in enumerate(
                sentence_tokens
            ):
                if (
                    token.lower_
                    not in self.STRUCTURAL_WORDS
                ):
                    continue

                start = index
                end = index + 1

                # ------------------------------------------------------
                # Extend to the left only through nominal/adjectival
                # material.
                # ------------------------------------------------------

                left_steps = 0

                while start > 0 and left_steps < 6:
                    previous = sentence_tokens[start - 1]

                    if self._can_extend_left(previous):
                        start -= 1
                        left_steps += 1
                        continue

                    # Preserve numeric hyphenated modifiers such as
                    # "15-minute" when the structural phrase begins
                    # at "minute".
                    if (
                        previous.is_punct
                        and previous.text == "-"
                        and start >= 2
                    ):
                        number = sentence_tokens[start - 2]

                        if number.like_num:
                            start -= 2
                            left_steps += 2
                            continue

                    break

                # ------------------------------------------------------
                # Extend to the right only when the following words
                # are clearly nominal.
                #
                # This prevents:
                #
                #     "Order Service The Order Service ..."
                #
                # style leakage.
                # ------------------------------------------------------

                right_steps = 0

                while (
                    end < len(sentence_tokens)
                    and right_steps < 2
                ):
                    following = sentence_tokens[
                        end
                    ]

                    if not self._can_extend_right(
                        following
                    ):
                        break

                    end += 1
                    right_steps += 1

                span = doc[
                    sentence_tokens[start].i :
                    sentence_tokens[end - 1].i + 1
                ]

                cleaned = self._clean_name(
                    span.text
                )

                if not cleaned:
                    continue

                results.append(
                    (
                        span,
                        "STRUCTURAL",
                        0.98,
                    )
                )

        return results

    def _extract_business_phrases(
        self,
        doc: Doc,
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        """
        Extract meaningful multi-word noun phrases.

        A single common noun is deliberately rejected.
        """

        results: list[
            tuple[Span, str | None, float]
        ] = []

        for sentence in doc.sents:
            for chunk in sentence.noun_chunks:
                if not self._valid_business_phrase(
                    chunk
                ):
                    continue

                results.append(
                    (
                        chunk,
                        "NOUN_PHRASE",
                        self._business_phrase_score(
                            chunk
                        ),
                    )
                )

        return results

    # ==================================================================
    # CANDIDATE FILTERING
    # ==================================================================

    def _clean_candidates(
        self,
        candidates: Iterable[
            tuple[Span, str | None, float]
        ],
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        results: list[
            tuple[Span, str | None, float]
        ] = []

        seen: set[
            tuple[int, int, str]
        ] = set()

        for span, label, score in candidates:
            name = self._clean_name(
                span.text
            )

            normalized = self._normalize(
                name
            )

            if not normalized:
                continue

            key = (
                span.start_char,
                span.end_char,
                normalized,
            )

            if key in seen:
                continue

            seen.add(key)

            results.append(
                (
                    span,
                    label,
                    score,
                )
            )

        return results

    def _filter_candidates(
        self,
        candidates: list[
            tuple[Span, str | None, float]
        ],
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        """
        Apply linguistic quality filters.

        No organization-specific vocabulary is used here.
        """

        results: list[
            tuple[Span, str | None, float]
        ] = []

        for span, label, score in candidates:
            tokens = [
                token
                for token in span
                if not token.is_space
                and not token.is_punct
            ]

            if not tokens:
                continue

            if len(tokens) > 7:
                continue

            name = self._clean_name(
                span.text
            )

            normalized = self._normalize(
                name
            )

            if not normalized:
                continue

            # ----------------------------------------------------------
            # Structural artifacts already have strong evidence.
            # ----------------------------------------------------------

            if label in {
                "API_PATTERN",
                "STRUCTURAL",
            }:
                results.append(
                    (
                        span,
                        label,
                        score,
                    )
                )
                continue

            # ----------------------------------------------------------
            # Explicit spaCy entities have strong evidence.
            # ----------------------------------------------------------

            if label in {
                "ORG",
                "PRODUCT",
                "FAC",
                "GPE",
                "EVENT",
                "LAW",
            }:
                results.append(
                    (
                        span,
                        label,
                        score,
                    )
                )
                continue

            # ----------------------------------------------------------
            # Remaining candidates must contain meaningful lexical
            # content.
            # ----------------------------------------------------------

            content_tokens = [
                token
                for token in tokens
                if not token.is_stop
                and token.pos_
                not in {
                    "DET",
                    "PRON",
                    "PUNCT",
                }
            ]

            if not content_tokens:
                continue

            if not any(
                token.pos_
                in {
                    "NOUN",
                    "PROPN",
                }
                for token in content_tokens
            ):
                continue

            # ----------------------------------------------------------
            # Single common nouns are too weak.
            # ----------------------------------------------------------

            if len(content_tokens) == 1:
                if not self._valid_single_token(
                    content_tokens[0],
                    label,
                ):
                    continue

            # ----------------------------------------------------------
            # Reject grammatical sentence fragments.
            # ----------------------------------------------------------

            if (
                tokens[0].lower_
                in {
                    "and",
                    "or",
                    "but",
                    "because",
                    "which",
                    "that",
                }
            ):
                continue

            if (
                tokens[-1].lower_
                in {
                    "and",
                    "or",
                    "but",
                    "because",
                    "which",
                    "that",
                }
            ):
                continue

            results.append(
                (
                    span,
                    label,
                    score,
                )
            )

        return results

    # ==================================================================
    # TOKEN / PHRASE VALIDATION
    # ==================================================================

    def _valid_single_token(
        self,
        token: Token,
        label: str | None,
    ) -> bool:
        word = token.lower_
        lemma = token.lemma_.lower()

        if word in self.STRUCTURAL_WORDS:
            return False

        if (
            word in self.GENERIC_WORDS
            or lemma in self.GENERIC_WORDS
        ):
            return False

        if token.pos_ != "PROPN":
            return False

        # Sentence-initial capitalization by itself is insufficient.
        if token.is_sent_start:
            if label in {
                "ORG",
                "PRODUCT",
                "FAC",
                "GPE",
            }:
                return True

            if self._looks_technical(
                token.text
            ):
                return True

            if self._has_internal_capitalization(
                token.text
            ):
                return True

            return False

        return True

    def _valid_business_phrase(
        self,
        span: Span,
    ) -> bool:
        tokens = [
            token
            for token in span
            if not token.is_space
            and not token.is_punct
        ]

        if not tokens:
            return False

        if len(tokens) > 7:
            return False

        content_tokens = [
            token
            for token in tokens
            if not token.is_stop
            and token.pos_
            not in {
                "DET",
                "PRON",
                "PUNCT",
            }
        ]

        if not content_tokens:
            return False

        if not any(
            token.pos_
            in {
                "NOUN",
                "PROPN",
            }
            for token in content_tokens
        ):
            return False

        # Single ordinary nouns are rejected.
        if len(content_tokens) == 1:
            return self._valid_single_token(
                content_tokens[0],
                None,
            )

        if span.root.pos_ not in {
            "NOUN",
            "PROPN",
        }:
            return False

        return True

    # ==================================================================
    # STRUCTURAL BOUNDARIES
    # ==================================================================

    @staticmethod
    def _is_hyphenated_numeric_modifier(
        tokens: list[Token],
        index: int,
    ) -> bool:
        """
        Return True when the token at `index` participates in a numeric
        hyphenated modifier such as:

            15-minute
            30-day
            4-hour

        This allows structural phrases to preserve the complete modifier
        instead of producing fragments such as "minute freshness standard".
        """
        if index < 2:
            return False

        current = tokens[index]
        separator = tokens[index - 1]
        number = tokens[index - 2]

        if current.pos_ not in {"NOUN", "PROPN", "ADJ"}:
            return False

        if not separator.is_punct or separator.text != "-":
            return False

        return number.like_num

    @staticmethod
    def _can_extend_left(
        token: Token,
    ) -> bool:
        if token.is_punct:
            return False

        if token.lower_ in {
            "and",
            "or",
            "but",
            "because",
            "which",
            "that",
            "this",
            "these",
            "those",
            "the",
            "a",
            "an",
        }:
            return False

        return token.pos_ in {
            "NOUN",
            "PROPN",
            "ADJ",
            "NUM",
        }

    @staticmethod
    def _can_extend_right(
        token: Token,
    ) -> bool:
        """
        Allow right-side extension only when the token is grammatically
        part of the nominal phrase.

        A bare NOUN/PROPN is not sufficient because sentence structures
        such as:

            "the freshness standard RateEngine must meet"

        can otherwise produce the invalid entity:

            "freshness standard RateEngine"

        Dependency-aware extension preserves legitimate compounds while
        preventing subjects, objects, and following clauses from leaking
        into the entity span.
        """
        if token.is_punct:
            return False

        if token.pos_ not in {
            "NOUN",
            "PROPN",
            "ADJ",
            "NUM",
        }:
            return False

        return token.dep_ in {
            "compound",
            "amod",
            "nmod",
            "flat",
            "fixed",
            "appos",
        }

    # ==================================================================
    # OVERLAP RESOLUTION
    # ==================================================================

    def _resolve_overlaps(
        self,
        candidates: list[
            tuple[Span, str | None, float]
        ],
    ) -> list[
        tuple[Span, str | None, float]
    ]:
        """
        Resolve candidates covering the same textual region.

        Structural artifacts take precedence over generic noun phrases.
        """

        ordered = sorted(
            candidates,
            key=lambda candidate: (
                -self._candidate_priority(
                    candidate
                ),
                candidate[0].start_char,
                candidate[0].end_char,
            ),
        )

        selected: list[
            tuple[Span, str | None, float]
        ] = []

        for candidate in ordered:
            span = candidate[0]

            discard = False

            for existing in list(selected):
                existing_span = existing[0]

                if not self._spans_overlap(
                    span,
                    existing_span,
                ):
                    continue

                candidate_name = self._normalize(
                    self._clean_name(
                        span.text
                    )
                )

                existing_name = self._normalize(
                    self._clean_name(
                        existing_span.text
                    )
                )

                # Same textual entity.
                if candidate_name == existing_name:
                    discard = True
                    break

                # Structural artifact beats generic noun phrase.
                if (
                    candidate[1] == "STRUCTURAL"
                    and existing[1]
                    not in {
                        "STRUCTURAL",
                        "API_PATTERN",
                    }
                ):
                    selected.remove(existing)
                    break

                if (
                    existing[1] == "STRUCTURAL"
                    and candidate[1]
                    not in {
                        "STRUCTURAL",
                        "API_PATTERN",
                    }
                ):
                    discard = True
                    break

                # If one completely contains the other, keep the
                # more informative candidate.
                if (
                    existing_span.start_char
                    <= span.start_char
                    and existing_span.end_char
                    >= span.end_char
                ):
                    discard = True
                    break

                if (
                    span.start_char
                    <= existing_span.start_char
                    and span.end_char
                    >= existing_span.end_char
                ):
                    selected.remove(existing)
                    break

            if not discard:
                selected.append(candidate)

        return selected

    @staticmethod
    def _spans_overlap(
        first: Span,
        second: Span,
    ) -> bool:
        return (
            first.start_char < second.end_char
            and second.start_char < first.end_char
        )

    # ==================================================================
    # ENTITY RECONCILIATION
    # ==================================================================

    def _reconcile_entities(
        self,
        candidates: list[
            tuple[Span, str | None, float]
        ],
    ) -> list[ExtractedEntity]:
        """
        Reconcile candidates by normalized name.

        Example:

            Payment Gateway → BUSINESS_CONCEPT
            Payment Gateway → SYSTEM

        becomes:

            Payment Gateway → SYSTEM

        The same normalized entity therefore cannot exist with two
        conflicting types.
        """

        records: dict[
            str,
            dict[str, object],
        ] = {}

        for span, label, score in candidates:
            name = self._clean_name(
                span.text
            )

            normalized = self._normalize(
                name
            )

            if not normalized:
                continue

            entity_type = self._classify(
                name,
                label,
            )

            if normalized not in records:
                records[normalized] = {
                    "name": name,
                    "types": {},
                    "best_score": score,
                }

            record = records[
                normalized
            ]

            types = record["types"]

            if not isinstance(types, dict):
                continue

            previous_score = float(
                types.get(
                    entity_type,
                    0.0,
                )
            )

            types[entity_type] = max(
                previous_score,
                score,
            )

            if score > float(
                record["best_score"]
            ):
                record["best_score"] = score
                record["name"] = name

        entities: list[
            ExtractedEntity
        ] = []

        for normalized, record in records.items():
            types = record["types"]

            if not isinstance(types, dict):
                continue

            entity_type = self._resolve_type(
                types
            )

            entities.append(
                ExtractedEntity(
                    name=str(
                        record["name"]
                    ),
                    normalized_name=normalized,
                    entity_type=entity_type,
                    description=None,
                )
            )

        return sorted(
            entities,
            key=lambda entity: (
                entity.name.lower(),
                entity.entity_type,
            ),
        )

    # ==================================================================
    # TYPE CLASSIFICATION
    # ==================================================================

    @classmethod
    def _classify(
        cls,
        name: str,
        spacy_label: str | None,
    ) -> str:
        normalized = cls._normalize(
            name
        )

        structural_type = (
            cls._structural_type(
                normalized
            )
        )

        if structural_type is not None:
            return structural_type

        if spacy_label == "ORG":
            if cls._looks_like_technology(normalized):
                return "SYSTEM"

            return "ORGANIZATION"

        if spacy_label in {
            "PRODUCT",
            "FAC",
        }:
            return "SYSTEM"

        if cls._looks_like_technology(
            normalized
        ):
            return "TECHNOLOGY"

        return "BUSINESS_CONCEPT"

    @classmethod
    def _structural_type(
        cls,
        normalized: str,
    ) -> str | None:
        tokens = set(
            normalized.split()
        )

        matches: list[
            tuple[int, str]
        ] = []

        for entity_type, markers in (
            cls.STRUCTURAL_MARKERS.items()
        ):
            if tokens & markers:
                matches.append(
                    (
                        cls.TYPE_PRIORITY[
                            entity_type
                        ],
                        entity_type,
                    )
                )

        if not matches:
            return None

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return matches[0][1]

    @classmethod
    def _resolve_type(
        cls,
        types: dict[str, float],
    ) -> str:
        """
        Resolve competing classifications.

        Structural artifact types always outrank the generic
        BUSINESS_CONCEPT classification.
        """

        return max(
            types,
            key=lambda entity_type: (
                cls.TYPE_PRIORITY.get(
                    entity_type,
                    0,
                ),
                float(
                    types[entity_type]
                ),
            ),
        )

    # ==================================================================
    # CANDIDATE SCORING
    # ==================================================================

    @classmethod
    def _candidate_priority(
        cls,
        candidate: tuple[
            Span,
            str | None,
            float,
        ],
    ) -> float:
        span, label, score = candidate

        priority = score

        if label == "API_PATTERN":
            priority += 2.0

        elif label == "STRUCTURAL":
            priority += 1.5

        structural_type = cls._structural_type(
            cls._normalize(
                cls._clean_name(
                    span.text
                )
            )
        )

        if structural_type is not None:
            priority += (
                cls.TYPE_PRIORITY[
                    structural_type
                ]
                / 100.0
            )

        return priority

    @staticmethod
    def _ner_score(
        span: Span,
    ) -> float:
        if span.label_ in {
            "ORG",
            "PRODUCT",
            "FAC",
        }:
            return 0.95

        return 0.85

    @staticmethod
    def _business_phrase_score(
        span: Span,
    ) -> float:
        content_tokens = [
            token
            for token in span
            if not token.is_stop
            and token.pos_
            not in {
                "DET",
                "PRON",
                "PUNCT",
            }
        ]

        if len(content_tokens) >= 3:
            return 0.72

        return 0.62

    # ==================================================================
    # TECHNOLOGY DETECTION
    # ==================================================================

    @classmethod
    def _looks_like_technology(
        cls,
        normalized: str,
    ) -> bool:
        tokens = normalized.split()

        for token in tokens:
            if re.fullmatch(
                r"[a-z][a-z0-9_-]*\d+(?:\.\d+)*",
                token,
            ):
                return True

        return any(
            token.endswith(
                (
                    "-framework",
                    "-library",
                    "-platform",
                    "-engine",
                )
            )
            or re.search(
                r"(?:Engine|Platform|Service|System)$",
                token,
                re.IGNORECASE,
            )
            for token in tokens
        )

    @staticmethod
    def _looks_technical(
        value: str,
    ) -> bool:
        return bool(
            re.search(
                r"(?:API|SDK|\d)",
                value,
            )
        )

    @staticmethod
    def _has_internal_capitalization(
        value: str,
    ) -> bool:
        return any(
            character.isupper()
            for character in value[1:]
        )

    # ==================================================================
    # NAME NORMALIZATION
    # ==================================================================

    @classmethod
    def _clean_name(
        cls,
        value: str,
    ) -> str:
        value = re.sub(
            r"\s+",
            " ",
            value.strip(),
        )

        tokens = value.split()

        # Remove grammatical determiners from the edges.
        while (
            len(tokens) > 1
            and tokens[0].lower()
            in cls.FUNCTION_WORDS
        ):
            tokens.pop(0)

        while (
            len(tokens) > 1
            and tokens[-1].lower()
            in cls.FUNCTION_WORDS
        ):
            tokens.pop()

        value = " ".join(tokens)

        # Normalize possessives.
        value = re.sub(
            r"\s*['’]s\b",
            "",
            value,
            flags=re.IGNORECASE,
        )

        return value.strip(
            " \t\r\n.,;:!?()[]{}<>\"'`"
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        value = value.lower().strip()

        value = re.sub(
            r"[^\w\s/-]",
            "",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()
