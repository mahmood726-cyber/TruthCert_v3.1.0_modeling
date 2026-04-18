import time
from pathlib import Path
from typing import Any, Dict, Optional

from .hash_utils import hash_doc_list, hash_file
from .models import ScopeLock
from .pipeline import run_bundle
from .config_utils import load_config, write_config
from .ledger import append_ledger
from .io_utils import write_json


FROZEN_THRESHOLDS = {
    "fact_agreement": 0.80,
    "interpretation_agreement": 0.70,
    "blindspot_r": 0.60,
    "material_disagreement_pct": 0.05,
}


def init_scope(args: Any) -> None:
    sources = [Path(p) for p in args.sources]
    doc_hashes = [hash_file(p) for p in sources]
    scope_hash = hash_doc_list(doc_hashes)
    scope = ScopeLock(
        endpoint=args.endpoint,
        entities=args.entities,
        units=args.units,
        timepoint=args.timepoint,
        inclusion_snippet=args.inclusion,
        source_hash=scope_hash,
    )
    write_config(Path(args.out), scope.to_dict())


def init_policy(args: Any) -> None:
    policy = {
        "scope_lock_ref": "scope-lock-1",
        "validator_version": "validators-2026-01",
        "validator_set_hash": "",
        "timestamp": time.time(),
        "thresholds": dict(FROZEN_THRESHOLDS),
        "witness_config": {
            "mode": args.mode,
            "min_witnesses": 3,
            "max_witnesses": 3 if args.mode == "fixed" else 5,
            "heterogeneity": args.heterogeneity,
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
    write_config(Path(args.out), policy)


def _resolve_path(base_dir: Path, path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        candidate = base_dir / path
        if candidate.exists():
            return candidate
        return path
    return path


def _load_provider_config(value: Any, base_dir: Path) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return load_config(_resolve_path(base_dir, value))
    raise SystemExit("provider_config must be a dict or path")


def _load_policy(path: Path) -> Dict[str, Any]:
    policy = load_config(path)
    if policy.get("thresholds") != FROZEN_THRESHOLDS:
        raise SystemExit("Policy thresholds must match frozen v3.1.0 values")
    return policy


def _run_single(
    mode: str,
    scope_path: Path,
    policy_path: Path,
    source_paths: list[Path],
    out_dir: Path,
    output_type: str,
    validator_set_path: Optional[Path],
    provider_name: str,
    provider_config: Optional[Dict[str, Any]],
    mock_noise: float,
) -> None:
    scope = ScopeLock.from_dict(load_config(scope_path))
    policy = _load_policy(policy_path)

    validator_set: Optional[Dict[str, Any]] = None
    if validator_set_path:
        validator_set = load_config(validator_set_path)

    result = run_bundle(
        scope=scope,
        policy=policy,
        source_paths=source_paths,
        mode=mode,
        output_type=output_type,
        validator_set=validator_set,
        mock_noise=mock_noise,
        provider_name=provider_name,
        provider_config=provider_config,
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    if "error" in result:
        write_json(out_dir / "error.json", result)
        raise SystemExit(result["error"])

    if mode == "Exploration":
        write_json(out_dir / "draft.json", result["draft"])
        append_ledger(out_dir / "ledger.jsonl", result["ledger"].to_dict())
        return

    bundle = result["bundle"]
    ledger = result["ledger"]

    write_json(out_dir / "bundle.json", {
        "bundle_id": bundle.bundle_id,
        "policy_anchor_ref": bundle.policy_anchor_ref,
        "scope_lock_ref": bundle.scope_lock_ref,
        "extracted_payload": bundle.extracted_payload,
        "gate_outcomes": [{"gate_id": g.gate_id, "passed": g.passed, "detail": g.detail} for g in bundle.gate_outcomes],
        "terminal_state": bundle.terminal_state,
        "timestamp": bundle.timestamp,
    })

    append_ledger(out_dir / "ledger.jsonl", ledger.to_dict())


def _run_manifest(manifest_path: Path) -> None:
    manifest = load_config(manifest_path)
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        raise SystemExit("Manifest must include a non-empty 'runs' list")

    base_dir = manifest_path.parent
    for idx, run in enumerate(runs, start=1):
        if not isinstance(run, dict):
            raise SystemExit("Each run entry must be a dict")

        mode = run.get("mode", "Verification")
        scope_path = _resolve_path(base_dir, run["scope"])
        policy_path = _resolve_path(base_dir, run["policy"])

        sources = run.get("sources")
        if isinstance(sources, str):
            sources = [sources]
        if not isinstance(sources, list) or not sources:
            raise SystemExit("Each run entry must include sources")
        source_paths = [_resolve_path(base_dir, s) for s in sources]

        out_dir_value = run.get("out_dir", f"out/run-{idx}")
        out_dir = _resolve_path(base_dir, out_dir_value)

        validator_set = run.get("validator_set")
        validator_set_path = _resolve_path(base_dir, validator_set) if validator_set else None

        output_type = run.get("output_type", "FACT")
        mock_noise = float(run.get("mock_noise", 0.0))
        provider_name = run.get("provider", "mock")
        provider_config = _load_provider_config(run.get("provider_config"), base_dir)

        _run_single(
            mode=mode,
            scope_path=scope_path,
            policy_path=policy_path,
            source_paths=source_paths,
            out_dir=out_dir,
            output_type=output_type,
            validator_set_path=validator_set_path,
            provider_name=provider_name,
            provider_config=provider_config,
            mock_noise=mock_noise,
        )


def run_cli(args: Any) -> None:
    if args.command == "init-scope":
        init_scope(args)
        return
    if args.command == "init-policy":
        init_policy(args)
        return
    if args.command == "run-bundles":
        _run_manifest(Path(args.manifest))
        return

    provider_config = _load_provider_config(args.provider_config, Path.cwd())

    _run_single(
        mode=args.mode,
        scope_path=Path(args.scope),
        policy_path=Path(args.policy),
        source_paths=[Path(p) for p in args.sources],
        out_dir=Path(args.out_dir),
        output_type=args.output_type,
        validator_set_path=Path(args.validator_set) if args.validator_set else None,
        provider_name=args.provider,
        provider_config=provider_config,
        mock_noise=args.mock_noise,
    )
