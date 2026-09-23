from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EvaluationMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def normalize_entity(value: str) -> str:
    return " ".join(value.strip().lower().split())


def calculate_metrics(
    predicted_entities: Iterable[str],
    gold_entities: Iterable[str],
) -> EvaluationMetrics:
    predicted = {
        normalize_entity(entity)
        for entity in predicted_entities
        if entity.strip()
    }

    gold = {
        normalize_entity(entity)
        for entity in gold_entities
        if entity.strip()
    }

    true_positives = len(predicted & gold)
    false_positives = len(predicted - gold)
    false_negatives = len(gold - predicted)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return EvaluationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )