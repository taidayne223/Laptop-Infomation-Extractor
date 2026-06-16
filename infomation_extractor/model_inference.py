from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


OFFLINE_MAPPING_DB = {
    # Apple Silicon MacBook Pro
    "mac16,6": "Apple MacBook Pro 14-inch (M4 Max, Late 2024)",
    "mac16,5": "Apple MacBook Pro 14-inch (M4 Pro, Late 2024)",
    "mac16,1": "Apple MacBook Pro 14-inch (M4, Late 2024)",
    "mac16,8": "Apple MacBook Pro 16-inch (M4 Pro, Late 2024)",
    "mac16,9": "Apple MacBook Pro 16-inch (M4 Max, Late 2024)",
    
    "mac15,3": "Apple MacBook Pro 14-inch (M3, Late 2023)",
    "mac15,6": "Apple MacBook Pro 14-inch (M3 Pro, Late 2023)",
    "mac15,8": "Apple MacBook Pro 14-inch (M3 Max, Late 2023)",
    "mac15,7": "Apple MacBook Pro 16-inch (M3 Pro, Late 2023)",
    "mac15,9": "Apple MacBook Pro 16-inch (M3 Max, Late 2023)",
    
    "mac14,7": "Apple MacBook Pro 13-inch (M2, 2022)",
    "mac14,5": "Apple MacBook Pro 14-inch (M2 Pro, Early 2023)",
    "mac14,9": "Apple MacBook Pro 14-inch (M2 Pro, Early 2023)",
    "mac14,6": "Apple MacBook Pro 14-inch (M2 Max, Early 2023)",
    "mac14,10": "Apple MacBook Pro 16-inch (M2 Pro, Early 2023)",
    "mac14,12": "Apple MacBook Pro 16-inch (M2 Max, Early 2023)",
    
    "macbookpro18,3": "Apple MacBook Pro 14-inch (M1 Pro, Late 2021)",
    "macbookpro18,4": "Apple MacBook Pro 14-inch (M1 Max, Late 2021)",
    "macbookpro18,1": "Apple MacBook Pro 16-inch (M1 Pro, Late 2021)",
    "macbookpro18,2": "Apple MacBook Pro 16-inch (M1 Max, Late 2021)",
    "macbookpro17,1": "Apple MacBook Pro 13-inch (M1, 2020)",

    # Apple Silicon MacBook Air
    "mac15,12": "Apple MacBook Air 13-inch (M3, 2024)",
    "mac15,13": "Apple MacBook Air 15-inch (M3, 2024)",
    "macbookair15,1": "Apple MacBook Air 15-inch (M2, 2023)",
    "macbookair14,2": "Apple MacBook Air 13-inch (M2, 2022)",
    "macbookair10,1": "Apple MacBook Air 13-inch (M1, 2020)",

    # Some popular Intel/AMD Windows Laptop SKU prefixes or models
    "82y8": "Lenovo Legion Slim 5 16IRH8",
    "82y9": "Lenovo Legion Slim 5 16IRH8",
    "82ud": "Lenovo Yoga Slim 7 ProX 14ARH7",
    "82v2": "Lenovo Legion Pro 7 16IRX8",
    "82wq": "Lenovo Legion Pro 7 16IRX8H",
    "82wm": "Lenovo Legion Pro 5 16IRX8",
    "83dg": "Lenovo Legion 5 16IRX9",
    "83dv": "Lenovo Legion Pro 5 16IRX9",
    "82xt": "Lenovo LOQ 15IRH8",
    "82xv": "Lenovo LOQ 15IRH8",
    "21d2": "Lenovo ThinkPad Z13 Gen 1",
    "21d3": "Lenovo ThinkPad Z16 Gen 1",
    "21e6": "Lenovo ThinkPad E14 Gen 4",
    "21e8": "Lenovo ThinkPad E15 Gen 4",
    "21ah": "Lenovo ThinkPad T14 Gen 3",
}


@dataclass
class ModelGuess:
    model_name: str
    confidence: float
    method: str
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    notes: str = ""


def infer_model(system_info: dict[str, Any], provider: Any = None) -> ModelGuess:
    summary = system_info.get("summary") or {}
    manufacturer = _clean(summary.get("manufacturer"))
    model = _clean(summary.get("marketing_model")) or _clean(summary.get("system_model"))
    model_code = _clean(summary.get("system_model"))
    sku = _clean(summary.get("system_sku"))
    baseboard = _clean(summary.get("baseboard"))

    # Gather candidates for database lookup
    candidates = []
    if sku:
        candidates.append((sku, f"System SKU/version: {sku}"))
    if model_code:
        candidates.append((model_code, f"System model: {model_code}"))
    if baseboard:
        candidates.append((baseboard, f"Baseboard: {baseboard}"))

    for cand_val, cand_desc in candidates:
        lowered = cand_val.lower().strip()
        for key, commercial_name in OFFLINE_MAPPING_DB.items():
            # Check for word matching or exact match
            words = re.findall(r'[a-z0-9]+', lowered)
            if key in words or lowered == key:
                evidence = [f"{cand_desc} matched offline DB key '{key}'"]
                if manufacturer:
                    evidence.append(f"Manufacturer: {manufacturer}")
                if model and model != cand_val:
                    evidence.append(f"Reported model: {model}")
                return ModelGuess(
                    model_name=commercial_name,
                    confidence=0.95,
                    method="offline_database",
                    evidence=evidence,
                    alternatives=[],
                    notes="Matched with offline model lookup database. High confidence.",
                )

    return heuristic_guess(system_info)


def heuristic_guess(system_info: dict[str, Any]) -> ModelGuess:
    summary = system_info.get("summary") or {}
    manufacturer = _clean(summary.get("manufacturer"))
    model = _clean(summary.get("marketing_model")) or _clean(summary.get("system_model"))
    model_code = _clean(summary.get("system_model"))
    sku = _clean(summary.get("system_sku"))
    baseboard = _clean(summary.get("baseboard"))
    cpu = _clean(summary.get("cpu"))

    evidence: list[str] = []
    if manufacturer:
        evidence.append(f"Manufacturer: {manufacturer}")
    if model:
        evidence.append(f"System model: {model}")
    if model_code and model_code != model:
        evidence.append(f"Model/product code: {model_code}")
    if sku:
        evidence.append(f"SKU/version: {sku}")
    if baseboard:
        evidence.append(f"Baseboard: {baseboard}")
    if cpu:
        evidence.append(f"CPU: {cpu}")

    parts = []
    if manufacturer and (not model or not model.lower().startswith(manufacturer.lower())):
        parts.append(manufacturer)
    if model:
        parts.append(model)
    if sku and not _sku_contains_marketing_name(sku, model) and sku.lower() not in " ".join(parts).lower():
        parts.append(sku)

    if not parts:
        parts = [system_info.get("platform") or "Unknown laptop"]

    confidence = 0.35
    if manufacturer and model:
        confidence = 0.62
    if manufacturer and model and sku:
        confidence = 0.74

    alternatives = []
    if model_code and model_code != model:
        alternatives.append("Search commercial name using model/product code: " + model_code)
    if baseboard and baseboard.lower() not in " ".join(parts).lower():
        alternatives.append("Search commercial name using baseboard/product code: " + baseboard)

    return ModelGuess(
        model_name=" ".join(parts).strip(),
        confidence=confidence,
        method="heuristic",
        evidence=evidence,
        alternatives=alternatives,
        notes="Local heuristic guess. Ask the cloud AI to verify the exact commercial variant.",
    )


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {
        "default string",
        "system product name",
        "system manufacturer",
        "to be filled by o.e.m.",
        "to be filled by oem",
        "unknown",
        "none",
    }:
        return None
    return text


def _sku_contains_marketing_name(sku: str, model: str | None) -> bool:
    if not model:
        return False
    normalized_sku = sku.lower().replace("_", " ")
    normalized_model = model.lower().replace("_", " ")
    return normalized_model in normalized_sku
