Operational Playbook

Policy presets
- balanced: fixed witnesses, heterogeneity preferred, budget warn
- safety: smart witnesses, heterogeneity required, gold standard on
- productivity: tiered witnesses, budget warn or hard depending on cost

Budget controls
- enforce max_tokens_per_bundle or max_cost_usd_per_bundle
- alert at alert_threshold_pct of budget

Monitoring
- false_ship_pct, reject_pct
- tokens_per_extracted_field
- adversarial_miss_rate
- late_consensus_pattern
- high_cost_failure_pattern

Governance
- Validator changes require minor version bump and human approval
- Ledger is append-only; store bundle hash and rerun recipe

Deployment checklist
- Validate ScopeLock binding to CleanState doc hashes
- Verify threshold freeze for v3.1.0
- Confirm heterogeneity rules (required/preferred)
- Test Gate B8 with different family
- Enable audit logging and access controls
