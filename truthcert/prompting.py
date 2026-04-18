from typing import Any, Dict


def build_prompt(parsed: Dict[str, Any], output_type: str) -> str:
    text = parsed.get("text", "")
    prompt = (
        "Extract numeric values from the source text. "
        "Return JSON with keys: numbers (array of numbers), total_numbers (int), output_type (string).\n"
        f"output_type={output_type}\n"
        "source_text:\n"
        f"{text}"
    )
    return prompt
