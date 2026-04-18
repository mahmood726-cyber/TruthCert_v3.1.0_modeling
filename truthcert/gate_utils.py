import math
from typing import Any, Dict, List, Tuple


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _rel_diff(a: float, b: float, eps: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), eps)


def flatten_payload(payload: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_payload(value, path))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                list_path = f"{path}.{idx}"
                if isinstance(item, dict):
                    flat.update(flatten_payload(item, list_path))
                else:
                    flat[list_path] = item
        else:
            flat[path] = value
    return flat


def majority_value(values: List[Any], material_pct: float, eps: float) -> Any:
    if not values:
        return None
    if all(_is_number(v) for v in values):
        return sorted(values)[len(values) // 2]
    counts: Dict[Any, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def values_match(a: Any, b: Any, material_pct: float, eps: float) -> bool:
    if _is_number(a) and _is_number(b):
        return _rel_diff(float(a), float(b), eps) <= material_pct
    return a == b


def compute_agreement(witness_payloads: List[Dict[str, Any]], material_pct: float, eps: float) -> Tuple[float, Dict[str, Any]]:
    flats = [flatten_payload(p) for p in witness_payloads]
    all_paths = sorted({k for f in flats for k in f.keys()})

    total = 0
    matches = 0
    majority_map: Dict[str, Any] = {}

    for path in all_paths:
        values = [f.get(path) for f in flats if path in f]
        maj = majority_value(values, material_pct, eps)
        majority_map[path] = maj
        for v in values:
            total += 1
            if values_match(v, maj, material_pct, eps):
                matches += 1

    agreement = matches / total if total > 0 else 0.0
    return agreement, majority_map


def pearson_r(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or len(xs) == 0:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def path_matches(pattern: str, path: str) -> bool:
    p_segments = pattern.split(".")
    segments = path.split(".")
    if len(p_segments) != len(segments):
        return False
    for ps, s in zip(p_segments, segments):
        if ps == "*":
            continue
        if ps != s:
            return False
    return True


def match_bound(bounds: Dict[str, Any], path: str) -> Any:
    if path in bounds:
        return bounds[path]
    for pattern, b in bounds.items():
        if "*" in pattern and path_matches(pattern.replace("[*]", "*"), path):  
            return b
    return None


def normalize_family(name: str) -> str:
    lower = name.strip().lower()
    if lower.startswith("openai gpt") or lower.startswith("gpt-"):
        return "OpenAI GPT"
    if lower.startswith("anthropic claude") or lower.startswith("claude"):
        return "Anthropic Claude"
    if lower.startswith("google gemini") or lower.startswith("gemini"):
        return "Google Gemini"
    return name
