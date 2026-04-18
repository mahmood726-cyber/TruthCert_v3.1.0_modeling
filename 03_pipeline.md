Execution Pipeline Design

Stages
1) Ingress
   - Load ScopeLock and PolicyAnchor
   - Initialize CleanState

2) Retrieval
   - Fetch source docs
   - Hash docs, update CleanState
   - Verify ScopeLock.source_hash binding

3) Parse + Arbitration
   - Primary parser
   - Alternate parser if unstable
   - Material disagreement check

4) Lane A (Exploration)
   - Minimal gates: parse arbitration, structural type/bounds, optional smoke tests
   - Emit DraftOutput

5) Lane B (Verification)
   - B1: Witness extraction (fixed/smart/tiered)
   - Witness provider adapter (mock/http) supplies extraction payloads
   - B1.5: Heterogeneity enforcement
   - B2: Blindspot test
   - B3: Structural validation (schema/types/bounds/totals/provenance)
   - B4: Anti-mixing + uncertainty rules
   - B5: Semantic agreement thresholds
   - B6: Escalation (helper differs by axis)
   - B7: Gold standard if enabled and triggered
   - B8: Adversarial corruption tests (different family)
   - B9: Terminal judgment
   - B10: RAG (optional; structure-only warnings)
   - B11: Efficiency tracking + budget enforcement

Witness orchestration
- Fixed: count = policy_anchor.witness_config.min_witnesses
- Smart: start at min_witnesses, stop if agreement >= convergence_threshold
- Tiered: witness count by complexity bucket
- Provider selection and config are per run (CLI or manifest)

Escalation triggers
- 70-79 percent agreement
- Provenance failures
- Endpoint mismatch
- Anti-mixing suspicion
- Uncertainty not derivable
- Fragile parse repair
- External discrepancies
- Heterogeneity preferred but unmet

Outputs
- DRAFT (Lane A) or SHIPPED/REJECTED (Lane B)
- Ledger entry always written
