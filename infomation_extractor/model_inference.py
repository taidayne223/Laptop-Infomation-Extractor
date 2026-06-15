from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelGuess:
    model_name: str
    confidence: float
    method: str
    evidence: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    notes: str = ""


def infer_model(system_info: dict[str, Any], provider: Any = None) -> ModelGuess:
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
