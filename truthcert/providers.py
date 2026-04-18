import json
import urllib.request
from typing import Any, Dict, List, Optional

from .parsers import extract_numbers
from .prompting import build_prompt


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def model_families(self) -> List[str]:
        return ["Mock"]

    def extract(self, parsed: Dict[str, Any], output_type: str, witness_index: int) -> Dict[str, Any]:
        raise NotImplementedError


class MockProvider(BaseProvider):
    def model_families(self) -> List[str]:
        families = self.config.get("model_families")
        if isinstance(families, list) and families:
            return families
        return ["OpenAI GPT", "Anthropic Claude", "Google Gemini"]

    def extract(self, parsed: Dict[str, Any], output_type: str, witness_index: int) -> Dict[str, Any]:
        numbers = list(parsed.get("numbers", []))
        mock_noise = float(self.config.get("mock_noise", 0.0))
        if mock_noise > 0:
            for idx, val in enumerate(numbers):
                if self._random_hit(mock_noise, witness_index, idx):
                    numbers[idx] = val * 1.1 + 0.5
        return {
            "numbers": numbers,
            "total_numbers": len(numbers),
            "output_type": output_type,
        }

    def _random_hit(self, probability: float, witness_index: int, value_index: int) -> bool:
        # Deterministic perturbation to keep runs reproducible without global RNG state.
        seed = (witness_index + 1) * 1000 + (value_index + 1) * 17
        return (seed % 100) < int(probability * 100)


class HttpProvider(BaseProvider):
    def model_families(self) -> List[str]:
        families = self.config.get("model_families")
        if isinstance(families, list) and families:
            return families
        models = self.config.get("models")
        if isinstance(models, list) and models:
            return [str(m) for m in models]
        return ["HttpProvider"]

    def extract(self, parsed: Dict[str, Any], output_type: str, witness_index: int) -> Dict[str, Any]:
        url = self.config.get("url")
        if not url:
            raise ProviderError("HttpProvider requires 'url' in provider config")

        prompt = build_prompt(parsed, output_type)
        payload = dict(self.config.get("request_template", {}))

        prompt_field = self.config.get("prompt_field", "prompt")
        payload[prompt_field] = prompt

        models = self.config.get("models")
        model_field = self.config.get("model_field")
        if model_field and isinstance(models, list) and models:
            payload[model_field] = models[witness_index % len(models)]

        headers = {"Content-Type": "application/json"}
        headers.update(self.config.get("headers", {}))

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        timeout = float(self.config.get("timeout_sec", 30))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_text = resp.read().decode("utf-8")

        return _response_to_payload(resp_text, self.config, output_type)


def _dig_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _response_to_payload(resp_text: str, config: Dict[str, Any], output_type: str) -> Dict[str, Any]:
    try:
        data = json.loads(resp_text)
    except json.JSONDecodeError:
        numbers = extract_numbers(resp_text)
        return {"numbers": numbers, "total_numbers": len(numbers), "output_type": output_type}

    response_path = config.get("response_path")
    if response_path:
        extracted = _dig_path(data, response_path)
        if isinstance(extracted, dict):
            return extracted
        if isinstance(extracted, str):
            numbers = extract_numbers(extracted)
            return {"numbers": numbers, "total_numbers": len(numbers), "output_type": output_type}

    if isinstance(data, dict):
        if "numbers" in data and "total_numbers" in data:
            return data
        if "text" in data and isinstance(data["text"], str):
            numbers = extract_numbers(data["text"])
            return {"numbers": numbers, "total_numbers": len(numbers), "output_type": output_type}

    raise ProviderError("Unable to extract payload from provider response")


def get_provider(name: str, config: Optional[Dict[str, Any]] = None) -> BaseProvider:
    if name == "mock":
        return MockProvider(config)
    if name == "http":
        return HttpProvider(config)
    raise ProviderError(f"Unknown provider: {name}")
