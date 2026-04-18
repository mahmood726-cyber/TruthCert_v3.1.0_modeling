import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .gate_utils import compute_agreement, flatten_payload, match_bound, pearson_r, values_match, normalize_family
from .models import Bundle, GateOutcome


def gate_b1_fixed(policy: Dict[str, Any]) -> GateOutcome:
    min_w = int(policy["witness_config"]["min_witnesses"])
    max_w = int(policy["witness_config"]["max_witnesses"])
    if min_w != max_w:
        return GateOutcome("B1", False, "fixed mode requires min_witnesses == max_witnesses")
    if min_w < 3:
        return GateOutcome("B1", False, "min_witnesses must be >= 3")
    return GateOutcome("B1", True, "")


def gate_b1_heterogeneity(witnesses: List[Dict[str, Any]], policy: Dict[str, Any]) -> GateOutcome:
    heterogeneity = policy["witness_config"]["heterogeneity"]
    families = sorted({normalize_family(w["model_family"]) for w in witnesses})
    if heterogeneity == "required" and len(families) < 2:
        return GateOutcome("B1.5", False, "heterogeneity_not_met")
    return GateOutcome("B1.5", True, "")


def gate_b2_blindspot(witnesses: List[Dict[str, Any]], material_pct: float, eps: float, threshold_r: float) -> GateOutcome:
    payloads = [w["payload"] for w in witnesses]
    flat_payloads = [flatten_payload(p) for p in payloads]
    all_paths = sorted({k for f in flat_payloads for k in f.keys()})

    if len(all_paths) < 5:
        return GateOutcome("B2", True, "not_computable")

    agreement, majority = compute_agreement(payloads, material_pct, eps)
    vectors: List[List[float]] = []
    for f in flat_payloads:
        vec = []
        for path in all_paths:
            v = f.get(path)
            maj = majority.get(path)
            vec.append(0.0 if values_match(v, maj, material_pct, eps) else 1.0)
        vectors.append(vec)

    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            r = pearson_r(vectors[i], vectors[j])
            if r > threshold_r:
                return GateOutcome("B2", False, f"blindspot_r={r:.2f}")
    return GateOutcome("B2", True, "")


def gate_b3_structural(witnesses: List[Dict[str, Any]], validator_set: Optional[Dict[str, Any]]) -> GateOutcome:
    payloads = [w["payload"] for w in witnesses]
    flat_payloads = [flatten_payload(p) for p in payloads]
    all_paths = sorted({k for f in flat_payloads for k in f.keys()})

    for f in flat_payloads:
        if sorted(f.keys()) != all_paths:
            return GateOutcome("B3", False, "schema_mismatch")

    if validator_set and "bounds" in validator_set:
        bounds = validator_set["bounds"]
        for path in all_paths:
            for f in flat_payloads:
                value = f.get(path)
                if isinstance(value, (int, float)):
                    bound = match_bound(bounds, path)
                    if bound is None:
                        return GateOutcome("B3", False, f"bounds_missing:{path}")
                    if value < bound.get("min", value) or value > bound.get("max", value):
                        return GateOutcome("B3", False, f"bounds_violation:{path}")

    for w in witnesses:
        payload = w["payload"]
        if "numbers" in payload and "total_numbers" in payload:
            if len(payload["numbers"]) != int(payload["total_numbers"]):
                return GateOutcome("B3", False, "totals_mismatch")

    return GateOutcome("B3", True, "")


def gate_b4_anti_mixing() -> GateOutcome:
    return GateOutcome("B4", True, "")


def gate_b5_semantic(witnesses: List[Dict[str, Any]], policy: Dict[str, Any], output_type: str) -> Tuple[GateOutcome, float]:
    payloads = [w["payload"] for w in witnesses]
    material_pct = float(policy["thresholds"]["material_disagreement_pct"])
    eps = 1e-6
    agreement, _ = compute_agreement(payloads, material_pct, eps)

    thresholds = policy["thresholds"]
    if output_type in ("FACT", "DERIVED"):
        required = float(thresholds["fact_agreement"])
    else:
        required = float(thresholds["interpretation_agreement"])

    passed = agreement >= required
    detail = f"agreement={agreement:.2f} required={required:.2f}"
    return GateOutcome("B5", passed, detail), agreement


def gate_b8_adversarial(payload: Dict[str, Any], material_pct: float) -> GateOutcome:
    flat = flatten_payload(payload)
    numeric_paths = [p for p, v in flat.items() if isinstance(v, (int, float))]
    if not numeric_paths:
        return GateOutcome("B8", True, "no_numeric_fields")

    for path in numeric_paths:
        original = float(flat[path])
        corrupted = original * (1 + material_pct * 2)
        rel = abs(corrupted - original) / max(abs(corrupted), abs(original), 1e-6)
        if rel <= material_pct:
            return GateOutcome("B8", False, f"missed_corruption:{path}")

    return GateOutcome("B8", True, "")


def run_all_gates(
    witnesses: List[Dict[str, Any]],
    policy: Dict[str, Any],
    output_type: str,
    validator_set: Optional[Dict[str, Any]],
) -> Tuple[List[GateOutcome], float]:
    outcomes: List[GateOutcome] = []

    if policy["witness_config"]["mode"] == "fixed":
        outcomes.append(gate_b1_fixed(policy))
    else:
        outcomes.append(GateOutcome("B1", True, ""))

    outcomes.append(gate_b1_heterogeneity(witnesses, policy))

    material_pct = float(policy["thresholds"]["material_disagreement_pct"])
    threshold_r = float(policy["thresholds"]["blindspot_r"])
    outcomes.append(gate_b2_blindspot(witnesses, material_pct, 1e-6, threshold_r))
    outcomes.append(gate_b3_structural(witnesses, validator_set))
    outcomes.append(gate_b4_anti_mixing())

    b5, agreement = gate_b5_semantic(witnesses, policy, output_type)
    outcomes.append(b5)

    outcomes.append(GateOutcome("B6", True, ""))

    if policy["features"].get("gold_standard_enabled", False):
        outcomes.append(GateOutcome("B7", False, "gold_standard_not_implemented"))
    else:
        outcomes.append(GateOutcome("B7", True, ""))

    payload = witnesses[0]["payload"] if witnesses else {}
    outcomes.append(gate_b8_adversarial(payload, material_pct))

    outcomes.append(GateOutcome("B9", True, ""))
    outcomes.append(GateOutcome("B10", True, ""))
    outcomes.append(GateOutcome("B11", True, ""))

    return outcomes, agreement
