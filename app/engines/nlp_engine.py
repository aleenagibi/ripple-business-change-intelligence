import re

import spacy


class NLPEngine:
    """Performs deterministic NLP preprocessing for Ripple documents."""

    def __init__(self) -> None:
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=["ner"],
        )

    def preprocess(self, text: str) -> str:
        """Normalize text while preserving meaningful business terms."""

        text = re.sub(r"\s+", " ", text).strip()

        doc = self.nlp(text)

        tokens = [
            token.lemma_.lower()
            for token in doc
            if token.is_alpha and not token.is_stop
        ]

        return " ".join(tokens)

    def chunk(
        self,
        text: str,
        max_tokens: int = 180,
        overlap: int = 30,
    ) -> list[str]:
        """
        Split text into overlapping semantic chunks.

        Chunks are sentence-aware and bounded by token count.
        """

        doc = self.nlp(text)

        sentences = [
            sentence.text.strip()
            for sentence in doc.sents
            if sentence.text.strip()
        ]

        chunks: list[str] = []
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_doc = self.nlp(sentence)
            sentence_tokens = len(
                [
                    token
                    for token in sentence_doc
                    if not token.is_space
                ]
            )

            if (
                current_sentences
                and current_tokens + sentence_tokens > max_tokens
            ):
                chunks.append(" ".join(current_sentences))

                overlap_sentences: list[str] = []
                overlap_tokens = 0

                for previous in reversed(current_sentences):
                    previous_doc = self.nlp(previous)
                    previous_count = len(
                        [
                            token
                            for token in previous_doc
                            if not token.is_space
                        ]
                    )

                    if overlap_tokens + previous_count > overlap:
                        break

                    overlap_sentences.insert(0, previous)
                    overlap_tokens += previous_count

                current_sentences = overlap_sentences
                current_tokens = overlap_tokens

            current_sentences.append(sentence)
            current_tokens += sentence_tokens

        if current_sentences:
            chunks.append(" ".join(current_sentences))

        return [
            chunk.strip()
            for chunk in chunks
            if chunk.strip()
        ]

    def token_count(self, text: str) -> int:
        """Return the number of NLP tokens in a text segment."""

        doc = self.nlp(text)

        return len(
            [
                token
                for token in doc
                if not token.is_space
            ]
        )