import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .hash_utils import hash_doc_list, hash_file, sha256_text
from .models import Bundle, CleanState, GateOutcome, LedgerEntry, ScopeLock
from .parsers import parse_docs
from .witnesses import run_witnesses
from .gates import run_all_gates
from .gate_utils import normalize_family


def init_clean_state() -> CleanState:
    return CleanState(
        environment_id=f"env-{int(time.time())}",
        source_documents=[],
        retrieval_timestamp=time.time(),
        input_hash="",
    )


def build_docs(paths: List[Path]) -> List[Dict[str, Any]]:
    docs = []
    for idx, path in enumerate(paths):
        content = path.read_text(encoding="utf-8")
        doc_hash = hash_file(path)
        docs.append({
            "doc_id": f"doc-{idx+1}",
            "path": str(path),
            "text": content,
            "doc_hash": doc_hash,
        })
    return docs


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def run_bundle(
    scope: ScopeLock,
    policy: Dict[str, Any],
    source_paths: List[Path],
    mode: str,
    output_type: str,
    validator_set: Optional[Dict[str, Any]],
    mock_noise: float,
    provider_name: str,
    provider_config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    clean_state = init_clean_state()
    docs = build_docs(source_paths)

    doc_hashes = [d["doc_hash"] for d in docs]
    scope_hash = hash_doc_list(doc_hashes)
    if scope_hash != scope.source_hash:
        return {"error": "scope_hash_mismatch", "expected": scope.source_hash, "actual": scope_hash}

    clean_state.source_documents = docs
    clean_state.input_hash = sha256_text("".join(doc_hashes))

    parsed_primary = parse_docs(docs)
    parsed = parsed_primary

    if mode == "Exploration":
        tokens_used = estimate_tokens(parsed.get("text", ""))
        draft_output = {
            "type": "CANDIDATE_FACT",
            "content": parsed,
            "parse_status": "stable" if parsed.get("stable", True) else "repaired",
            "risk_flags": {
                "mixing_suspicion": False,
                "missing_provenance": True,
                "uncertainty_unknown": True,
                "failed_tests": [],
                "external_mismatch": False,
            },
            "efficiency": {
                "tokens_used": tokens_used,
                "under_budget": True,
                "budget_enforcement": policy["cost_budget"]["enforcement"],
            },
        }

        ledger_entry = LedgerEntry(
            bundle_id=f"bundle-{int(time.time())}",
            bundle_hash=sha256_text(json.dumps(draft_output, sort_keys=True)),
            policy_anchor_ref=policy["scope_lock_ref"],
            rerun_recipe={
                "scope_lock": scope.to_dict(),
                "policy_anchor": policy,
                "sources": [str(p) for p in source_paths],
                "mode": mode,
                "output_type": output_type,
                "provider": provider_name,
                "provider_config": provider_config,
            },
            gate_outcomes={"A1": True, "A2": True, "A3": True},
            failure_reasons=[],
            terminal_state="DRAFT",
            timestamp=time.time(),
            memory_fields={
                "failure_signature": "",
                "source_context": ",".join([Path(d["path"]).suffix for d in docs]),
                "correction_hint": "",
                "embedding": [0.0] * 768,
                "similar_past_failures": [],
            },
            efficiency_fields={
                "witnesses_used": 0,
                "witnesses_converged_at": None,
                "total_tokens_input": tokens_used,
                "total_tokens_output": 0,
                "total_tokens": tokens_used,
                "estimated_cost_usd": tokens_used * 0.000002,
                "tokens_per_extracted_field": tokens_used,
                "latency_ms": 0,
                "early_termination": False,
                "early_termination_reason": "",
                "budget_enforcement": policy["cost_budget"]["enforcement"],
                "budget_limit_tokens": policy["cost_budget"].get("max_tokens_per_bundle"),
                "budget_limit_usd": policy["cost_budget"].get("max_cost_usd_per_bundle"),
                "budget_exceeded": False,
                "heterogeneity_required": policy["witness_config"]["heterogeneity"] == "required",
                "heterogeneity_achieved": False,
                "model_families_used": [],
            },
            external_refs=None,
        )

        return {
            "draft": draft_output,
            "ledger": ledger_entry,
        }

    witnesses = run_witnesses(
        parsed,
        policy,
        output_type,
        provider_name,
        provider_config,
        mock_noise,
    )
    gate_outcomes, agreement = run_all_gates(witnesses, policy, output_type, validator_set)

    terminal_state = "SHIPPED" if all(g.passed for g in gate_outcomes) else "REJECTED"

    bundle = Bundle(
        bundle_id=f"bundle-{int(time.time())}",
        policy_anchor_ref=policy["scope_lock_ref"],
        scope_lock_ref=policy["scope_lock_ref"],
        extracted_payload=witnesses[0]["payload"] if witnesses else {},
        provenance={},
        gate_outcomes=gate_outcomes,
        terminal_state=terminal_state,
        timestamp=time.time(),
    )

    total_input_tokens = sum(estimate_tokens(d["text"]) for d in docs) * max(1, len(witnesses))
    total_output_tokens = estimate_tokens(json.dumps(bundle.extracted_payload)) * max(1, len(witnesses))
    total_tokens = total_input_tokens + total_output_tokens
    estimated_cost_usd = total_tokens * 0.000002

    failure_reasons = [g.gate_id for g in gate_outcomes if not g.passed]

    efficiency_fields = {
        "witnesses_used": len(witnesses),
        "witnesses_converged_at": None,
        "total_tokens_input": total_input_tokens,
        "total_tokens_output": total_output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "tokens_per_extracted_field": total_tokens / max(1, len(bundle.extracted_payload)),
        "latency_ms": 0,
        "early_termination": False,
        "early_termination_reason": "",
        "budget_enforcement": policy["cost_budget"]["enforcement"],
        "budget_limit_tokens": policy["cost_budget"].get("max_tokens_per_bundle"),
        "budget_limit_usd": policy["cost_budget"].get("max_cost_usd_per_bundle"),
        "budget_exceeded": False,
        "heterogeneity_required": policy["witness_config"]["heterogeneity"] == "required",
        "heterogeneity_achieved": len({normalize_family(w["model_family"]) for w in witnesses}) >= 2,
        "model_families_used": sorted({normalize_family(w["model_family"]) for w in witnesses}),
    }

    memory_fields = {
        "failure_signature": "+".join(failure_reasons),
        "source_context": ",".join([Path(d["path"]).suffix for d in docs]),
        "correction_hint": "",
        "embedding": [0.0] * 768,
        "similar_past_failures": [],
    }

    ledger_entry = LedgerEntry(
        bundle_id=bundle.bundle_id,
        bundle_hash=sha256_text(json.dumps(bundle.extracted_payload, sort_keys=True)),
        policy_anchor_ref=policy["scope_lock_ref"],
        rerun_recipe={
            "scope_lock": scope.to_dict(),
            "policy_anchor": policy,
            "sources": [str(p) for p in source_paths],
            "mode": mode,
            "output_type": output_type,
            "provider": provider_name,
            "provider_config": provider_config,
        },
        gate_outcomes={g.gate_id: g.passed for g in gate_outcomes},
        failure_reasons=failure_reasons,
        terminal_state=terminal_state,
        timestamp=time.time(),
        memory_fields=memory_fields,
        efficiency_fields=efficiency_fields,
        external_refs=None,
    )

    return {
        "bundle": bundle,
        "ledger": ledger_entry,
        "agreement": agreement,
    }
