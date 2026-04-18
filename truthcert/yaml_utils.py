from typing import Any, Dict, List, Tuple


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def _parse_scalar(value: str) -> Any:
    val = value.strip()
    if not val:
        return ""
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    if val.lower() in ("null", "none", "~"):
        return None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        if "." in val or "e" in val or "E" in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def _split_key_value(content: str) -> Tuple[str, str]:
    if ":" not in content:
        raise ValueError(f"Invalid YAML mapping line: {content}")
    key, rest = content.split(":", 1)
    return key.strip(), rest.strip()


def _preprocess(text: str) -> List[Tuple[int, str]]:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        clean = _strip_comment(raw).rstrip("\n")
        if not clean.strip():
            continue
        indent = len(clean) - len(clean.lstrip(" "))
        content = clean.strip()
        lines.append((indent, content))
    return lines


def _parse_block(lines: List[Tuple[int, str]], start: int, indent: int) -> Tuple[Any, int]:
    if start >= len(lines):
        return None, start

    is_list = lines[start][0] == indent and lines[start][1].startswith("- ")
    if is_list:
        result: List[Any] = []
        i = start
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
            item = lines[i][1][2:].strip()
            if not item:
                if i + 1 < len(lines) and lines[i + 1][0] > indent:
                    value, i = _parse_block(lines, i + 1, lines[i + 1][0])
                else:
                    value = None
                    i += 1
                result.append(value)
                continue

            if ":" in item and not item.startswith('"') and not item.startswith("'"):
                key, rest = _split_key_value(item)
                if rest == "":
                    if i + 1 < len(lines) and lines[i + 1][0] > indent:
                        value, i = _parse_block(lines, i + 1, lines[i + 1][0])
                    else:
                        value = None
                        i += 1
                else:
                    value = _parse_scalar(rest)
                    i += 1
                result.append({key: value})
                continue

            result.append(_parse_scalar(item))
            i += 1
        return result, i

    result_dict: Dict[str, Any] = {}
    i = start
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        key, rest = _split_key_value(lines[i][1])
        if rest == "":
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                value, i = _parse_block(lines, i + 1, lines[i + 1][0])
            else:
                value = None
                i += 1
        else:
            value = _parse_scalar(rest)
            i += 1
        result_dict[key] = value
    return result_dict, i


def load_yaml(text: str) -> Any:
    lines = _preprocess(text)
    if not lines:
        return None
    result, _ = _parse_block(lines, 0, lines[0][0])
    return result


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in [":", "#", "\n"]) or text.strip() != text:
        return '"' + text.replace('"', '\\"') + '"'
    return text


def dump_yaml(data: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(data, dict):
        lines: List[str] = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(dump_yaml(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_dump_scalar(value)}")
        return "\n".join(lines)
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(dump_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {_dump_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{_dump_scalar(data)}"
