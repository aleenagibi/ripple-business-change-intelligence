from app.evaluation.metrics import calculate_metrics


PREDICTED_ENTITIES = {
    "4 business hours",
    "Platform",
    "CarrierConnect API",
    "error code RATE-409",
    "Q4 2025 booking volume",
    "Rates",
    "Rate Dispute Resolution Policy",
    "bindable rate quote",
    "Pricing & Rates",
    "credit memo",
    "RateEngine",
    "Rates Team",
    "BillingCore rate ledger",
    "Helix ticket",
    "service",
    "RATE-409",
    "BUSINESS OBJECTIVE",
    "15-minute freshness threshold",
    "Carrier Relations",
    "new error-code messaging",
    "Rate Dispute Resolution SOP",
    "RDP-002",
    "SOP-RDR-02",
    "Meridian TMS",
    "1 hour",
    "- Steps",
    "Initial GA release",
    "internal system",
    "pricing service",
    "BillingCore",
    "RateEngine changes",
    "business rules",
    "Knowledge Base",
    "Step",
    "System Documentation SD",
}


# Only include entities confirmed from the source documents
# as genuinely affected by the RATE-409 resolution-window change.
GOLD_ENTITIES = {
    "4 business hours",
    "RATE-409",
    "error code RATE-409",
    "Rates",
    "Rate Dispute Resolution Policy",
    "Pricing & Rates",
    "RateEngine",
    "Rates Team",
    "BillingCore rate ledger",
    "Rate Dispute Resolution SOP",
    "RDP-002",
    "SOP-RDR-02",
    "Shipment Booking Workflow",
    "WF-SB-01",
    "Resolving Rate Quote Errors",
    "Knowledge Base",
    "BRD-RE2-0091",
    "BillingCore",
}


def main() -> None:
    metrics = calculate_metrics(
        predicted_entities=PREDICTED_ENTITIES,
        gold_entities=GOLD_ENTITIES,
    )

    print("\nRipple — Test 1 Evaluation")
    print("=" * 32)
    print(f"Predicted entities : {len(PREDICTED_ENTITIES)}")
    print(f"Gold entities      : {len(GOLD_ENTITIES)}")
    print(f"True positives     : {metrics.true_positives}")
    print(f"False positives    : {metrics.false_positives}")
    print(f"False negatives    : {metrics.false_negatives}")
    print(f"Precision          : {metrics.precision:.4f}")
    print(f"Recall             : {metrics.recall:.4f}")
    print(f"F1                 : {metrics.f1:.4f}")


if __name__ == "__main__":
    main()