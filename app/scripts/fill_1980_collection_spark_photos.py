from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
APP_DATA = ROOT / "app" / "data" / "app-data.json"
PHOTO_OVERRIDES = ROOT / "app" / "data" / "model_photo_overrides.json"
SPARK_API = "https://rapi.sparkmodel.com"
SPARK_CDN = "https://minimax.fra1.cdn.digitaloceanspaces.com/published"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def compact(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).lower())


def get_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Codex F1 1:43 catalog photo import",
            "Accept": "application/json",
            "Content-Language": "en",
        },
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def spark_product(code: str) -> dict | None:
    url = f"{SPARK_API}/products?{urlencode({'q': code})}"
    data = get_json(url).get("data", [])
    exact = [
        item
        for item in data
        if compact(item.get("code")) == compact(code)
        and clean(item.get("scale_name")) == "1:43"
        and clean(item.get("brand_name")).lower() == "spark"
    ]
    if not exact:
        return None
    exact.sort(key=lambda item: 0 if str(item.get("ranking_year")) == "1980" else 1)
    return exact[0]


def spark_images(product_id: str, primary: str) -> list[str]:
    urls: list[str] = []
    if primary:
        urls.append(primary)
    data = get_json(f"{SPARK_API}/products/{product_id}/images?sort=position").get("data", [])
    for image_id in data:
        for suffix in [".webp", "-desktop-1x.avif"]:
            url = f"{SPARK_CDN}/{image_id}{suffix}"
            if url not in urls:
                urls.append(url)
    return urls


def main() -> None:
    app_data = json.loads(APP_DATA.read_text(encoding="utf-8"))
    overrides = json.loads(PHOTO_OVERRIDES.read_text(encoding="utf-8"))
    added: list[str] = []
    skipped: list[str] = []

    for item in app_data["collectionItems"]:
        if str(item.get("season")) != "1980":
            continue
        if clean(item.get("manufacturer")).lower() != "spark":
            continue
        code = clean(item.get("catalogNumber"))
        if not code:
            continue
        key = clean(item.get("id"))
        if key in overrides and (overrides[key].get("mainPhoto") or overrides[key].get("thumbnails")):
            continue
        try:
            product = spark_product(code)
            if not product:
                skipped.append(f"{key}: not found")
                continue
            urls = spark_images(product["product_id"], clean(product.get("primary_image_url")))
            if not urls:
                skipped.append(f"{key}: no images")
                continue
            overrides[key] = {
                "mainPhoto": urls[0],
                "thumbnails": urls[1:8],
                "originalPhotoUrl": urls[0],
                "sourcePageUrl": f"https://www.sparkmodel.com/products/{product['product_id']}",
            }
            added.append(f"{key}: {product.get('name')}")
            time.sleep(0.1)
        except Exception as exc:
            skipped.append(f"{key}: {type(exc).__name__}: {exc}")

    PHOTO_OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"added": added, "skipped": skipped}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
