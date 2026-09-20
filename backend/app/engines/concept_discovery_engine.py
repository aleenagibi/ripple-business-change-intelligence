import re
from collections import Counter
from dataclasses import dataclass

import spacy
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass(frozen=True)
class ConceptCandidate:
    """A candidate business concept discovered from an organization corpus."""

    name: str
    normalized_name: str
    frequency: int
    importance: float


class ConceptDiscoveryEngine:
    """
    Discovers organization-specific concepts from document chunks.

    The engine does not depend on a predefined list of business terms.
    Candidate concepts are derived from linguistic structure and ranked
    using corpus statistics.
    """

    def __init__(
        self,
        min_frequency: int = 1,
        max_phrase_length: int = 5,
    ) -> None:
        self.nlp = spacy.load("en_core_web_sm")
        self.min_frequency = min_frequency
        self.max_phrase_length = max_phrase_length

    def discover(
        self,
        texts: list[str],
        top_k: int = 100,
    ) -> list[ConceptCandidate]:
        """Discover and rank candidate concepts from document chunks."""

        if not texts:
            return []

        cleaned_texts = [
            text.strip()
            for text in texts
            if text and text.strip()
        ]

        if not cleaned_texts:
            return []

        candidates = self._extract_candidates(
            cleaned_texts
        )

        if not candidates:
            return []

        importance_scores = self._calculate_importance(
            cleaned_texts,
            candidates,
        )

        frequency = Counter(
            candidate
            for candidate in candidates
        )

        results = []

        for candidate, count in frequency.items():
            if count < self.min_frequency:
                continue

            results.append(
                ConceptCandidate(
                    name=candidate,
                    normalized_name=self._normalize(
                        candidate
                    ),
                    frequency=count,
                    importance=importance_scores.get(
                        candidate,
                        0.0,
                    ),
                )
            )

        results.sort(
            key=lambda item: (
                item.importance,
                item.frequency,
            ),
            reverse=True,
        )

        return results[:top_k]

    def _extract_candidates(
        self,
        texts: list[str],
    ) -> list[str]:
        candidates: list[str] = []

        for text in texts:
            doc = self.nlp(text)

            for chunk in doc.noun_chunks:
                phrase = self._clean_phrase(
                    chunk.text
                )

                if not self._is_valid_candidate(
                    phrase
                ):
                    continue

                candidates.append(phrase)

            for entity in doc.ents:
                phrase = self._clean_phrase(
                    entity.text
                )

                if not self._is_valid_candidate(
                    phrase
                ):
                    continue

                candidates.append(phrase)

        return candidates

    def _calculate_importance(
        self,
        texts: list[str],
        candidates: list[str],
    ) -> dict[str, float]:
        unique_candidates = list(
            dict.fromkeys(candidates)
        )

        if not unique_candidates:
            return {}

        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            stop_words="english",
            sublinear_tf=True,
        )

        try:
            matrix = vectorizer.fit_transform(
                texts
            )
        except ValueError:
            return {
                candidate: 0.0
                for candidate in unique_candidates
            }

        feature_names = vectorizer.get_feature_names_out()

        feature_index = {
            feature: index
            for index, feature in enumerate(
                feature_names
            )
        }

        scores: dict[str, float] = {}

        for candidate in unique_candidates:
            normalized = self._normalize(
                candidate
            )

            tokens = normalized.split()

            token_indices = [
                feature_index[token]
                for token in tokens
                if token in feature_index
            ]

            if not token_indices:
                scores[candidate] = 0.0
                continue

            score = float(
                matrix[:, token_indices]
                .mean()
            )

            scores[candidate] = score

        return scores

    def _is_valid_candidate(
        self,
        phrase: str,
    ) -> bool:
        if not phrase:
            return False

        tokens = phrase.split()

        if len(tokens) > self.max_phrase_length:
            return False

        if len(phrase) < 3:
            return False

        if not any(
            character.isalpha()
            for character in phrase
        ):
            return False

        normalized = self._normalize(
            phrase
        )

        if normalized in {
            "thing",
            "something",
            "example",
            "way",
            "time",
            "part",
            "kind",
            "type",
            "number",
            "people",
        }:
            return False

        return True

    @staticmethod
    def _clean_phrase(
        phrase: str,
    ) -> str:
        phrase = phrase.strip()

        phrase = re.sub(
            r"\s+",
            " ",
            phrase,
        )

        phrase = phrase.strip(
            ".,;:!?()[]{}\"'"
        )

        return phrase

    @staticmethod
    def _normalize(
        phrase: str,
    ) -> str:
        normalized = phrase.lower().strip()

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"[^\w\s-]",
            "",
            normalized,
        )

        return normalized