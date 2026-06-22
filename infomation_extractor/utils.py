from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SENSITIVE_KEY_PARTS = (
    "serial",
    "uuid",
    "udid",
    "uid",
    "guid",
    "identifyingnumber",
    "identifying_number",
    "service tag",
    "servicetag",
    "registrypath",
    "registry_path",
    "pspath",
    "deviceid",
    "device_id",
    "pnpdeviceid",
    "pnp_device_id",
    "instanceid",
    "instance_id",
    "monitorid",
    "monitor_id",
    "computername",
    "computer_name",
    "hostname",
    "host_name",
    "node",
    "username",
    "user_name",
    "owner",
    "email",
    "macaddress",
    "mac_address",
    "mac address",
    "ethernetaddress",
    "ethernet_address",
    "ethernet address",
    "ipaddress",
    "ip_address",
    "ip address",
    "ipv4",
    "ipv6",
    "ssid",
    "network name",
    "current network",
    "device_address",
    "device address",
    "local_address",
    "local address",
    "volumelabel",
    "volume_label",
    "volume label",
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
            safe_key = redact_sensitive_text(str(key))
            if is_sensitive_key(str(key)):
                clean[safe_key] = "[REDACTED]"
            else:
                clean[safe_key] = redact_sensitive(value)
        return clean
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    if isinstance(data, str):
        return redact_sensitive_text(data)
    return data


def redact_sensitive_text(value: str) -> str:
    value = re.sub(r"/Users/[^/\\\s]+", "/Users/[REDACTED]", value)
    value = re.sub(r"(?i)C:\\Users\\[^\\/\s]+", r"C:\\Users\\[REDACTED]", value)
    value = re.sub(r"(?i)[A-Z]:\\Users\\[^\\/\s]+", r"[DRIVE]:\\Users\\[REDACTED]", value)
    value = re.sub(
        r"\b[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\b",
        "[REDACTED]",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b", "[REDACTED_MAC]", value, flags=re.IGNORECASE)
    value = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]", value)
    value = re.sub(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", "[REDACTED_EMAIL]", value)
    value = re.sub(
        r"\b(iPhone|iPad|MacBook(?: Pro| Air)?|Apple Watch|AirPods?)\s+của\s+[^,\n\r\"/\\]+",
        r"\1 của [REDACTED]",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b[A-Z][\w .'-]{1,50}'s\s+(iPhone|iPad|MacBook(?: Pro| Air)?|Apple Watch|AirPods?)\b",
        r"[REDACTED]'s \1",
        value,
    )
    return value


def to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
