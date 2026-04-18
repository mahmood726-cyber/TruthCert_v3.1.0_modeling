import re
from typing import Any, Dict, List


def extract_numbers(text: str) -> List[float]:
    numbers = []
    for match in re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", text):
        try:
            numbers.append(float(match))
        except ValueError:
            continue
    return numbers


def parse_docs(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined_text = "\n".join(d["text"] for d in docs)
    numbers = extract_numbers(combined_text)
    stable = "PARSE_UNSTABLE" not in combined_text
    return {
        "stable": stable,
        "text": combined_text,
        "numbers": numbers,
    }
