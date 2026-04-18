Simulation Harness (Annex E aligned)

Scenario schema
- id: string
- domain: enum
- n_fields: int
- n_critical_fields: int
- corruption_rate: float
- parser_instability_rate: float
- mixing_pressure: float
- uncertainty_rate: float

Harness flow
1) Generate scenario list with fixed seed
2) Synthesize source documents and ground truth
3) Inject corruptions per registry
4) Run full Lane B pipeline
5) Score outcomes (bundle-correct, false-ship, reject)
6) Aggregate metrics into simulation_report

Outcomes
- bundle-correct: all critical fields correct and provenance valid
- false-ship: SHIPPED and not bundle-correct
- reject rate: REJECTED

Metrics
- shipped_pct
- false_ship_pct
- reject_pct
- mean_tokens_per_bundle
- tokens_per_correct_shipped
- early_termination_rate

Validator iteration loop
- Cluster failure signatures
- Propose new validators
- Re-run harness and check regression
- Bump validator version on approval
