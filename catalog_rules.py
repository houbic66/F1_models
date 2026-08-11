from __future__ import annotations

import re
import unicodedata
from typing import Any


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def deaccent(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", clean(value)) if not unicodedata.combining(ch))


def compact_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", deaccent(clean(value)).lower())


def norm_text(value: Any) -> str:
    value = deaccent(clean(value)).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def manufacturer_key(value: Any) -> str:
    return compact_key(value)


def is_spark_manufacturer(value: Any) -> bool:
    return manufacturer_key(value) == "spark" or bool(re.search(r"\bspark\b", clean(value), flags=re.I))


def is_minichamps_manufacturer(value: Any) -> bool:
    return manufacturer_key(value) == "minichamps" or bool(re.search(r"\bminichamps\b", clean(value), flags=re.I))


def extract_minichamps_code(*values: Any) -> str:
    for value in values:
        text = clean(value)
        match = re.search(r"\b(\d{3})\s*-?\s*(\d{6})\b", text)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        compact = compact_key(text)
        match = re.search(r"(\d{9})", compact)
        if match:
            return match.group(1)
    return ""


def extract_spark_code(*values: Any) -> str:
    for value in values:
        text = clean(value)
        match = re.search(r"\b(?:SPK|SP|S)\s*-?\s*(\d{4})\b", text, flags=re.I)
        if match:
            return f"S{match.group(1)}"
        compact = compact_key(text).upper()
        if re.fullmatch(r"S\d{4}", compact):
            return compact
        if re.fullmatch(r"SPK\d{4}", compact):
            return f"S{compact[3:]}"
        if re.fullmatch(r"SP\d{4}", compact):
            return f"S{compact[2:]}"
    return ""


def canonical_display_code(manufacturer: Any, catalog_number: Any, *search_texts: Any) -> str:
    """Return the code form used as the application's visible catalog key."""
    manufacturer_text = clean(manufacturer)
    values = (catalog_number, *search_texts)
    if is_minichamps_manufacturer(manufacturer_text):
        return extract_minichamps_code(*values)
    if is_spark_manufacturer(manufacturer_text):
        return extract_spark_code(*values)
    return clean(catalog_number)


def infer_manufacturer(manufacturer: Any, catalog_number: Any = "", *search_texts: Any) -> str:
    text = clean(manufacturer)
    if text:
        return text
    values = (catalog_number, *search_texts)
    if extract_spark_code(*values):
        return "Spark"
    if extract_minichamps_code(*values):
        return "Minichamps"
    return ""


def canonical_match_code(catalog_number: Any, manufacturer: Any = "", *search_texts: Any) -> str:
    """Return the strict comparison key used for matching catalog rows to the collection."""
    code = canonical_display_code(manufacturer, catalog_number, *search_texts)
    if is_spark_manufacturer(manufacturer) and code:
        return code.lower()
    if is_minichamps_manufacturer(manufacturer) and code:
        return code
    return compact_key(code or catalog_number)


NON_F1_PATTERNS = [
    r"\bformula\s*2\b",
    r"\bf2\b",
    r"\bformula\s*3\b",
    r"\bf3\b",
    r"\bgerman\s*f3\b",
    r"\bf\.?\s*ford\b",
    r"\bformula\s*ford\b",
    r"\bbritish\s*f\.?\s*ford\b",
    r"\bindy\s*car\b",
    r"\bindycar\b",
    r"\bcart\b",
    r"\bindy\s*500\b",
    r"\ble\s*mans\b",
    r"\bsportscar\b",
    r"\bgt\b",
    r"\bdtm\b",
    r"\btouring\s*car\b",
    r"\bralt\s+toyota\s+rt3\b",
    r"\bvan\s+diemen\s+rf81\b",
]


def is_non_f1_text(*values: Any) -> bool:
    text = " ".join(clean(value) for value in values)
    return any(re.search(pattern, text, flags=re.I) for pattern in NON_F1_PATTERNS)


def is_non_f1_model(model: dict[str, Any], field_names: list[str]) -> bool:
    return is_non_f1_text(*(model.get(field, "") for field in field_names))
