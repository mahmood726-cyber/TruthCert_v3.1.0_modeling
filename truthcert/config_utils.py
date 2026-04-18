from pathlib import Path
from typing import Any, Dict
import json
import os
import re

from .yaml_utils import load_yaml, dump_yaml


_ENV_PATTERN = re.compile(r"\$\{(?:ENV:)?([A-Z0-9_]+)\}")


def _expand_env_in_string(value: str) -> str:
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in os.environ:
            raise SystemExit(f"Missing environment variable: {key}")
        return os.environ[key]

    return _ENV_PATTERN.sub(replacer, value)


def _expand_env_vars(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _expand_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    if isinstance(data, str):
        return _expand_env_in_string(data)
    return data


def load_config(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = load_yaml(text)
    return _expand_env_vars(data)


def write_config(path: Path, data: Dict[str, Any]) -> None:
    suffix = path.suffix.lower()
    if suffix in (".yml", ".yaml"):
        path.write_text(dump_yaml(data) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
