from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW_CATALOG = ROOT / "outputs" / "model_catalog" / "sourced_model_catalog_expanded_raw.json"
PHOTO_OVERRIDES = ROOT / "app" / "data" / "model_photo_overrides.json"

SPARK_API = "https://rapi.sparkmodel.com/products"
SPARK_PRODUCT_URL = "https://www.sparkmodel.com/products/"
FORMULA_1_CLASSIC = "e4b7b927-094c-4585-8a2c-879dc7b68c49"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", clean(value).lower()).strip("-")


def model_id(manufacturer: str, code: str) -> str:
    return f"{slug(manufacturer)}__{slug(code)}"


def fetch_products(season: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        params = {
            "q": "",
            "page_number": page,
            "page_size": 100,
            "filters": json.dumps(
                [
                    'scale_name = "1:43"',
                    f'year = "{season}"',
                    f'category_ids = "{FORMULA_1_CLASSIC}"',
                ]
            ),
            "facets": json.dumps(
                [
                    "manufacturer_name",
                    "scale_name",
                    "brand_name",
                    "model_name",
                    "category_ids",
                    "ranking_competition_name",
                    "driver_names",
                    "year",
                ]
            ),
        }
        url = SPARK_API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 Codex F1 catalog", "Content-Language": "en"},
        )
        payload = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace"))
        data = payload.get("data") or []
        rows.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.1)
    return rows


def car_number_from(name: str, product: dict[str, Any]) -> str:
    ranking_number = clean(product.get("ranking_car_number"))
    if ranking_number:
        return ranking_number
    match = re.search(r"\bNo\.?\s*([0-9]{1,3}[A-Z]?)\b", name, flags=re.I)
    if match:
        return match.group(1)
    match = re.search(r"\bn\.?\s*([0-9]{1,3}[A-Z]?)\b", name, flags=re.I)
    return match.group(1) if match else ""


def event_from(name: str, product: dict[str, Any]) -> str:
    event = clean(product.get("ranking_competition_name"))
    if event:
        return event
    first_line = clean(name.split("\n", 1)[0])
    first_line = re.sub(r"\bNo\.?\s*[0-9]{1,3}[A-Z]?\b", " ", first_line, flags=re.I)
    first_line = re.sub(r"\bn\.?\s*[0-9]{1,3}[A-Z]?\b", " ", first_line, flags=re.I)
    first_line = re.sub(r"\b19\d{2}\b", " ", first_line)
    first_line = re.sub(re.escape(clean(product.get("manufacturer_name"))), " ", first_line, flags=re.I)
    first_line = re.sub(re.escape(clean(product.get("model_name"))), " ", first_line, flags=re.I)
    first_line = re.sub(r"\b(?:winner|practice|nq|dnq|\d+(?:st|nd|rd|th))\b", " ", first_line, flags=re.I)
    return clean(first_line)


def driver_from(name: str, product: dict[str, Any]) -> str:
    drivers = product.get("driver_names") or []
    if drivers:
        return clean(" / ".join(drivers))
    lines = [clean(part) for part in name.splitlines() if clean(part)]
    if len(lines) > 1:
        return lines[-1]
    match = re.search(r"(?:-|,)\s*([A-Z][A-Za-zÀ-ž .'-]+)$", name)
    return clean(match.group(1)) if match else ""


def row_from_product(product: dict[str, Any], season: str) -> dict[str, str]:
    name = clean(product.get("name"))
    code = clean(product.get("code"))
    manufacturer = clean(product.get("brand_name")) or "Spark"
    product_id = clean(product.get("product_id") or product.get("id"))
    source_url = SPARK_PRODUCT_URL + product_id if product_id else ""
    constructor = clean(product.get("manufacturer_name"))
    chassis = clean(product.get("model_name") or product.get("model_fullname"))
    driver = driver_from(name, product)
    return {
        "year": season,
        "constructor_car": constructor,
        "chassis_type": chassis,
        "driver": driver,
        "car_number": car_number_from(name, product),
        "team_livery": "",
        "race_gp_version": event_from(name, product),
        "manufacturer": manufacturer,
        "model_code": code,
        "scale": clean(product.get("scale_name")) or "1:43",
        "source_url": source_url,
        "source_name": "Spark official catalog API",
        "raw_title": name,
        "limited_edition": "",
        "price_aud": "",
        "notes": "Official Spark Formula 1 Classic 1:43 category",
    }


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def merge_raw(rows: list[dict[str, str]]) -> int:
    raw = load_json(RAW_CATALOG, [])
    existing = {
        (
            clean(row.get("source_name")),
            clean(row.get("manufacturer")),
            clean(row.get("model_code")),
            clean(row.get("year")),
        )
        for row in raw
    }
    added = 0
    for row in rows:
        key = (row["source_name"], row["manufacturer"], row["model_code"], row["year"])
        if key in existing:
            continue
        raw.append(row)
        existing.add(key)
        added += 1
    RAW_CATALOG.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def merge_photos(products: list[dict[str, Any]]) -> int:
    overrides = load_json(PHOTO_OVERRIDES, {})
    added = 0
    for product in products:
        code = clean(product.get("code"))
        image = clean(product.get("primary_image_url"))
        if not code or not image:
            continue
        key = model_id("Spark", code)
        product_id = clean(product.get("product_id") or product.get("id"))
        source_url = SPARK_PRODUCT_URL + product_id if product_id else ""
        record = overrides.get(key)
        if isinstance(record, dict) and (record.get("mainPhoto") or record.get("main")):
            continue
        overrides[key] = {
            "mainPhoto": image,
            "thumbnails": [],
            "originalPhotoUrl": image,
            "sourcePageUrl": source_url,
        }
        added += 1
    PHOTO_OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="1981")
    args = parser.parse_args()
    products = fetch_products(args.season)
    rows = [row_from_product(product, args.season) for product in products]
    added_rows = merge_raw(rows)
    added_photos = merge_photos(products)
    print(
        json.dumps(
            {
                "season": args.season,
                "sparkOfficialProducts": len(products),
                "rawRowsAdded": added_rows,
                "photoOverridesAdded": added_photos,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
