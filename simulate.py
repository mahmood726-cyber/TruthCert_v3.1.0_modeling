import argparse
import json
import random
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from truthcert.hash_utils import hash_doc_list, hash_file
from truthcert.models import ScopeLock
from truthcert.pipeline import run_bundle
from truthcert.gate_utils import _rel_diff


FROZEN_THRESHOLDS = {
    "fact_agreement": 0.80,
    "interpretation_agreement": 0.70,
    "blindspot_r": 0.60,
    "material_disagreement_pct": 0.05,
}


@dataclass
class Scenario:
    scenario_id: str
    domain: str
    n_fields: int
    n_critical_fields: int
    corruption_rate: float
    parser_instability_rate: float
    mixing_pressure: float
    uncertainty_rate: float


def generate_numbers(rng: random.Random, n_fields: int) -> List[float]:
    return [round(rng.uniform(1.0, 100.0), 2) for _ in range(n_fields)]


def apply_corruption(rng: random.Random, numbers: List[float], corruption_rate: float) -> Tuple[List[float], List[str]]:
    observed = list(numbers)
    applied: List[str] = []
    for idx in range(len(observed)):
        if rng.random() >= corruption_rate:
            continue
        choice = rng.choice(["decimal_shift", "sign_flip", "value_swap"])
        if choice == "decimal_shift":
            observed[idx] = observed[idx] * 10.0
        elif choice == "sign_flip":
            observed[idx] = -observed[idx]
        elif choice == "value_swap" and len(observed) > 1:
            swap_idx = (idx + 1) % len(observed)
            observed[idx], observed[swap_idx] = observed[swap_idx], observed[idx]
        applied.append(f"{choice}:{idx}")
    return observed, applied


def make_source_text(observed_numbers: List[float], parse_unstable: bool, scenario_id: str) -> str:
    numbers_str = ", ".join(str(n) for n in observed_numbers)
    text = f"Scenario\nNumbers: {numbers_str}\n"
    if parse_unstable:
        text += "PARSE_UNSTABLE\n"
    return text


def bundle_correct(payload: Dict[str, Any], true_numbers: List[float], n_critical: int, material_pct: float) -> bool:
    numbers = payload.get("numbers")
    if not isinstance(numbers, list):
        return False
    if len(numbers) < n_critical:
        return False
    eps = 1e-6
    for idx in range(n_critical):
        if not isinstance(numbers[idx], (int, float)):
            return False
        if _rel_diff(float(numbers[idx]), float(true_numbers[idx]), eps) > material_pct:
            return False
    return True


def build_policy() -> Dict[str, Any]:
    return {
        "scope_lock_ref": "scope-lock-sim",
        "validator_version": "validators-2026-01",
        "validator_set_hash": "",
        "timestamp": time.time(),
        "thresholds": dict(FROZEN_THRESHOLDS),
        "witness_config": {
            "mode": "fixed",
            "min_witnesses": 3,
            "max_witnesses": 3,
            "heterogeneity": "preferred",
            "convergence_threshold": 0.92,
        },
        "cost_budget": {
            "enforcement": "warn",
            "max_tokens_per_bundle": 50000,
            "max_cost_usd_per_bundle": 5.0,
            "alert_threshold_pct": 0.80,
        },
        "features": {
            "external_refs_enabled": False,
            "rag_enabled": False,
            "gold_standard_enabled": False,
        },
        "promotion_policy": "balanced",
    }


def run_simulation(
    n_scenarios: int,
    seed: int,
    out_dir: Path,
    models: List[str],
    enforce_adversarial: bool,
) -> None:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    scenario_records: List[Dict[str, Any]] = []
    result_records: List[Dict[str, Any]] = []

    domains = ["clinical", "finance", "policy", "science"]
    corruption_rates = [0.0, 0.05, 0.1, 0.2]
    parser_rates = [0.0, 0.05, 0.1]
    mixing_rates = [0.0, 0.2, 0.4]
    uncertainty_rates = [0.0, 0.05, 0.1]

    policy = build_policy()
    validator_set = {
        "bounds": {
            "numbers.*": {"min": 0, "max": 100},
            "total_numbers": {"min": 0, "max": 200},
        }
    }

    shipped = 0
    rejected = 0
    false_ship = 0
    correct_shipped = 0
    missed_adversarial = 0
    total_tokens = 0
    total_tokens_correct = 0

    workload_mix = Counter()

    for i in range(n_scenarios):
        n_fields = rng.randint(3, 12)
        n_critical_fields = max(1, n_fields // 3)
        scenario = Scenario(
            scenario_id=f"scn-{i+1:04d}",
            domain=rng.choice(domains),
            n_fields=n_fields,
            n_critical_fields=n_critical_fields,
            corruption_rate=rng.choice(corruption_rates),
            parser_instability_rate=rng.choice(parser_rates),
            mixing_pressure=rng.choice(mixing_rates),
            uncertainty_rate=rng.choice(uncertainty_rates),
        )

        true_numbers = generate_numbers(rng, scenario.n_fields)
        observed_numbers, corruptions = apply_corruption(rng, true_numbers, scenario.corruption_rate)
        parse_unstable = rng.random() < scenario.parser_instability_rate
        source_text = make_source_text(observed_numbers, parse_unstable, scenario.scenario_id)

        scenario_dir = out_dir / "sources"
        scenario_dir.mkdir(exist_ok=True)
        source_path = scenario_dir / f"{scenario.scenario_id}.txt"
        source_path.write_text(source_text, encoding="utf-8")

        doc_hash = hash_file(source_path)
        scope = ScopeLock(
            endpoint="endpoint",
            entities=["A", "B"],
            units="units",
            timepoint="t0",
            inclusion_snippet="sim",
            source_hash=hash_doc_list([doc_hash]),
        )

        provider_config = {
            "model_families": ["OpenAI GPT"],
            "models": models,
            "mock_noise": scenario.uncertainty_rate,
        }

        result = run_bundle(
            scope=scope,
            policy=policy,
            source_paths=[source_path],
            mode="Verification",
            output_type="FACT",
            validator_set=validator_set,
            mock_noise=scenario.uncertainty_rate,
            provider_name="mock",
            provider_config=provider_config,
        )

        if "error" in result:
            terminal_state = "REJECTED"
            shipped_flag = False
            bundle_correct_flag = False
            tokens_used = 0
        else:
            bundle = result["bundle"]
            ledger = result["ledger"]
            terminal_state = bundle.terminal_state
            shipped_flag = terminal_state == "SHIPPED"
            bundle_correct_flag = bundle_correct(
                bundle.extracted_payload,
                true_numbers,
                scenario.n_critical_fields,
                policy["thresholds"]["material_disagreement_pct"],
            )
            tokens_used = int(ledger.efficiency_fields.get("total_tokens", 0))

        if shipped_flag and corruptions:
            missed_adversarial += 1
            if enforce_adversarial:
                shipped_flag = False
                terminal_state = "REJECTED"

        if shipped_flag:
            shipped += 1
            if bundle_correct_flag:
                correct_shipped += 1
                total_tokens_correct += tokens_used
            else:
                false_ship += 1
        else:
            rejected += 1

        total_tokens += tokens_used
        workload_mix[scenario.domain] += 1

        scenario_records.append({
            "scenario": {
                "id": scenario.scenario_id,
                "domain": scenario.domain,
                "n_fields": scenario.n_fields,
                "n_critical_fields": scenario.n_critical_fields,
                "corruption_rate": scenario.corruption_rate,
                "parser_instability_rate": scenario.parser_instability_rate,
                "mixing_pressure": scenario.mixing_pressure,
                "uncertainty_rate": scenario.uncertainty_rate,
            },
            "true_numbers": true_numbers,
            "observed_numbers": observed_numbers,
            "corruptions": corruptions,
        })

        result_records.append({
            "scenario_id": scenario.scenario_id,
            "terminal_state": terminal_state,
            "shipped": shipped_flag,
            "bundle_correct": bundle_correct_flag,
            "tokens": tokens_used,
            "corruptions": corruptions,
            "missed_adversarial": bool(corruptions) and not bundle_correct_flag,
        })

    shipped_pct = shipped / n_scenarios if n_scenarios else 0.0
    false_ship_pct = false_ship / n_scenarios if n_scenarios else 0.0
    reject_pct = rejected / n_scenarios if n_scenarios else 0.0
    mean_tokens_per_bundle = total_tokens / n_scenarios if n_scenarios else 0.0
    tokens_per_correct_shipped = (total_tokens_correct / correct_shipped) if correct_shipped else 0.0

    report = {
        "simulation_report": {
            "n_scenarios": n_scenarios,
            "workload_mix": dict(workload_mix),
            "mode": "Verification",
            "heterogeneity": policy["witness_config"]["heterogeneity"],
            "budget_enforcement": policy["cost_budget"]["enforcement"],
            "shipped_pct": round(shipped_pct, 4),
            "false_ship_pct": round(false_ship_pct, 4),
            "reject_pct": round(reject_pct, 4),
            "mean_tokens_per_bundle": round(mean_tokens_per_bundle, 2),
            "tokens_per_correct_shipped": round(tokens_per_correct_shipped, 2),
            "early_termination_rate": 0.0,
            "missed_adversarial_pct": round(missed_adversarial / n_scenarios, 4) if n_scenarios else 0.0,
            "enforce_adversarial": enforce_adversarial,
        }
    }

    (out_dir / "scenarios.jsonl").write_text(
        "\n".join(json.dumps(r) for r in scenario_records) + "\n",
        encoding="utf-8",
    )
    (out_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(r) for r in result_records) + "\n",
        encoding="utf-8",
    )
    (out_dir / "simulation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TruthCert simulation runner")
    parser.add_argument("--n", type=int, default=1000, help="Number of scenarios")
    parser.add_argument("--seed", type=int, default=202601, help="Random seed")
    parser.add_argument("--out-dir", default="simulations", help="Output directory")
    parser.add_argument("--models", default="gpt-4o,gpt-4.1,gpt-4.1-mini", help="Comma-separated model labels")
    parser.add_argument("--enforce-adversarial", action="store_true", help="Reject shipped bundles when corruptions are present")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    run_simulation(args.n, args.seed, Path(args.out_dir), models, args.enforce_adversarial)


if __name__ == "__main__":
    main()
