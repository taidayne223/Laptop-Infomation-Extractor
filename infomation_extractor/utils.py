from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SENSITIVE_KEY_PARTS = (
    "serial",
    "uuid",
    "identifyingnumber",
    "identifying_number",
    "service tag",
    "servicetag",
)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(value: str, fallback: str = "laptop") -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if is_sensitive_key(str(key)):
                clean[key] = "[REDACTED]"
            else:
                clean[key] = redact_sensitive(value)
        return clean
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    return data


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
