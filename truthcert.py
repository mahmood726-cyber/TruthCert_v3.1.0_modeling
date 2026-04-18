import argparse

from truthcert.cli import run_cli


def main() -> None:
    parser = argparse.ArgumentParser(prog="truthcert", description="TruthCert v3.1.0 reference CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_scope = subparsers.add_parser("init-scope", help="Create a Scope Lock file")
    init_scope.add_argument("--sources", nargs="+", required=True, help="Source document paths")
    init_scope.add_argument("--out", required=True, help="Output path for scope_lock.json")
    init_scope.add_argument("--endpoint", required=True)
    init_scope.add_argument("--entities", nargs="+", required=True)
    init_scope.add_argument("--units", required=True)
    init_scope.add_argument("--timepoint", required=True)
    init_scope.add_argument("--inclusion", required=True)

    init_policy = subparsers.add_parser("init-policy", help="Create a Policy Anchor file")
    init_policy.add_argument("--out", required=True, help="Output path for policy_anchor.json")
    init_policy.add_argument("--mode", choices=["fixed", "smart", "tiered"], default="fixed")
    init_policy.add_argument("--heterogeneity", choices=["required", "preferred"], default="preferred")

    run = subparsers.add_parser("run", help="Run a TruthCert bundle")
    run.add_argument("--mode", choices=["Exploration", "Verification"], required=True)
    run.add_argument("--scope", required=True, help="Scope Lock JSON path")
    run.add_argument("--policy", required=True, help="Policy Anchor JSON path")
    run.add_argument("--sources", nargs="+", required=True, help="Source document paths")
    run.add_argument("--out-dir", required=True, help="Output directory")
    run.add_argument("--validator-set", help="Optional validator set JSON path")
    run.add_argument("--output-type", choices=["FACT", "DERIVED", "INTERPRETATION", "HYPOTHESIS"], default="FACT")
    run.add_argument("--mock-noise", type=float, default=0.0, help="Probability of numeric perturbation per value")
    run.add_argument("--provider", default="mock", help="Provider name (mock|http)")
    run.add_argument("--provider-config", help="Provider config JSON/YAML path")

    run_bundles = subparsers.add_parser("run-bundles", help="Run multiple bundles from a manifest file")
    run_bundles.add_argument("--manifest", required=True, help="Manifest JSON/YAML path")

    args = parser.parse_args()
    run_cli(args)


if __name__ == "__main__":
    main()
