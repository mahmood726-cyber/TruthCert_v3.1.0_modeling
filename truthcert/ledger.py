import json
from pathlib import Path
from typing import Any, Dict


def append_ledger(path: Path, entry: Dict[str, Any]) -> None:
    line = json.dumps(entry, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
