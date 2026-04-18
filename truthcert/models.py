import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScopeLock:
    endpoint: str
    entities: List[str]
    units: str
    timepoint: str
    inclusion_snippet: str
    source_hash: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ScopeLock":
        return ScopeLock(
            endpoint=data["endpoint"],
            entities=list(data["entities"]),
            units=data["units"],
            timepoint=data["timepoint"],
            inclusion_snippet=data["inclusion_snippet"],
            source_hash=data["source_hash"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "entities": self.entities,
            "units": self.units,
            "timepoint": self.timepoint,
            "inclusion_snippet": self.inclusion_snippet,
            "source_hash": self.source_hash,
        }


@dataclass
class PolicyAnchor:
    scope_lock_ref: str
    validator_version: str
    validator_set_hash: str
    timestamp: float
    thresholds: Dict[str, float]
    witness_config: Dict[str, Any]
    cost_budget: Dict[str, Any]
    features: Dict[str, bool]
    promotion_policy: str

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PolicyAnchor":
        return PolicyAnchor(
            scope_lock_ref=data["scope_lock_ref"],
            validator_version=data["validator_version"],
            validator_set_hash=data.get("validator_set_hash", ""),
            timestamp=float(data["timestamp"]),
            thresholds=dict(data["thresholds"]),
            witness_config=dict(data["witness_config"]),
            cost_budget=dict(data["cost_budget"]),
            features=dict(data["features"]),
            promotion_policy=data["promotion_policy"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope_lock_ref": self.scope_lock_ref,
            "validator_version": self.validator_version,
            "validator_set_hash": self.validator_set_hash,
            "timestamp": self.timestamp,
            "thresholds": self.thresholds,
            "witness_config": self.witness_config,
            "cost_budget": self.cost_budget,
            "features": self.features,
            "promotion_policy": self.promotion_policy,
        }


@dataclass
class CleanState:
    environment_id: str
    source_documents: List[Dict[str, Any]]
    retrieval_timestamp: float
    input_hash: str


@dataclass
class GateOutcome:
    gate_id: str
    passed: bool
    detail: str = ""


@dataclass
class Bundle:
    bundle_id: str
    policy_anchor_ref: str
    scope_lock_ref: str
    extracted_payload: Dict[str, Any]
    provenance: Dict[str, Any]
    gate_outcomes: List[GateOutcome]
    terminal_state: str
    timestamp: float


@dataclass
class LedgerEntry:
    bundle_id: str
    bundle_hash: str
    policy_anchor_ref: str
    rerun_recipe: Dict[str, Any]
    gate_outcomes: Dict[str, bool]
    failure_reasons: List[str]
    terminal_state: str
    timestamp: float
    memory_fields: Dict[str, Any]
    efficiency_fields: Dict[str, Any]
    external_refs: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "policy_anchor_ref": self.policy_anchor_ref,
            "rerun_recipe": self.rerun_recipe,
            "gate_outcomes": self.gate_outcomes,
            "failure_reasons": self.failure_reasons,
            "terminal_state": self.terminal_state,
            "timestamp": self.timestamp,
            "memory_fields": self.memory_fields,
            "efficiency_fields": self.efficiency_fields,
            "external_refs": self.external_refs,
        }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
