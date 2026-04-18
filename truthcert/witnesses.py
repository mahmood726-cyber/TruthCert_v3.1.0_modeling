from typing import Any, Dict, List, Optional

from .providers import get_provider


def run_witnesses(
    parsed: Dict[str, Any],
    policy: Dict[str, Any],
    output_type: str,
    provider_name: str,
    provider_config: Optional[Dict[str, Any]],
    mock_noise: float,
) -> List[Dict[str, Any]]:
    mode = policy["witness_config"]["mode"]
    min_w = int(policy["witness_config"]["min_witnesses"])
    max_w = int(policy["witness_config"]["max_witnesses"])

    if mode == "fixed":
        count = min_w
    elif mode == "smart":
        count = min_w
    else:
        n_fields = len(parsed.get("numbers", []))
        if n_fields < 5:
            count = 3
        elif n_fields <= 15:
            count = 4
        else:
            count = 5

    if provider_config is None:
        provider_config = {}
    provider_config = dict(provider_config)
    provider_config.setdefault("mock_noise", mock_noise)
    provider = get_provider(provider_name, provider_config)
    families = provider.model_families()
    models = provider_config.get("models")

    witnesses: List[Dict[str, Any]] = []
    for i in range(count):
        family = families[i % len(families)]
        payload = provider.extract(parsed, output_type, i)
        witness = {
            "witness_id": f"w{i+1}",
            "model_family": family,
            "payload": payload,
        }
        if isinstance(models, list) and models:
            witness["model_id"] = models[i % len(models)]
        witnesses.append(witness)

    if mode == "smart" and count < max_w:
        family = families[count % len(families)]
        payload = provider.extract(parsed, output_type, count)
        witness = {
            "witness_id": f"w{count+1}",
            "model_family": family,
            "payload": payload,
        }
        if isinstance(models, list) and models:
            witness["model_id"] = models[count % len(models)]
        witnesses.append(witness)

    return witnesses
