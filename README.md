TruthCert v3.1.0 Modeling Pack

This folder contains a minimal, runnable reference implementation and supporting docs.
Everything is ASCII and uses only the Python standard library.

Quick start
1) Create example configs:
   python truthcert.py init-scope --sources examples\source.txt --out examples\scope_lock.json --endpoint "endpoint" --entities "A" "B" --units "units" --timepoint "t0" --inclusion "demo"
   python truthcert.py init-policy --out examples\policy_anchor.json

2) Run verification:
   python truthcert.py run --mode Verification --scope examples\scope_lock.json --policy examples\policy_anchor.json --sources examples\source.txt --out-dir out

3) Run multiple bundles from a manifest:
   python truthcert.py run-bundles --manifest examples\manifest.json
   python truthcert.py run-bundles --manifest examples\manifest_gpt_mock.json

4) Run a 1000-scenario simulation:
   python simulate.py --n 1000 --out-dir simulations_1000
   python simulate.py --n 1000 --out-dir simulations_1000_strict --enforce-adversarial

Notes
- Config files can be JSON or YAML (.json/.yml/.yaml).
- Providers are pluggable; use --provider mock (default) or --provider http with a provider config.
- Manifest paths are resolved relative to the manifest file when possible.
- Provider configs support env vars with ${ENV:VAR} (or ${VAR}) in string fields.
- Z.ai template config is in `examples/provider_config_zai.json` (fill endpoint, model, response_path).
- GPT mock config is in `examples/provider_config_gpt_mock.json` (single family with multiple model labels).
- Simulation outputs: `simulation_report.json`, `scenarios.jsonl`, `results.jsonl` under the chosen output directory.

Files
- 01_schema.yaml: Canonical data model and validation rules
- 02_state_machine.mmd: State machine for Exploration and Verification
- 03_pipeline.md: Execution pipeline design and gate ordering
- 04_reference_workflow.py: Minimal reference workflow skeleton
- 05_simulation_harness.md: Annex E-aligned simulation harness plan
- 06_ops_playbook.md: Policy presets, budgets, monitoring, governance
- truthcert.py: CLI entry point
- truthcert/: Python modules implementing the pipeline
- examples/: Example inputs, manifest, and provider config
