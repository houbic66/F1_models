from __future__ import annotations

import argparse
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "app" / "data"
APP_DATA = DATA_DIR / "app-data.json"
PHOTO_OVERRIDES = DATA_DIR / "model_photo_overrides.json"
CACHE_DIR = DATA_DIR / "photo_page_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def cache_path(url: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:180]
    return CACHE_DIR / f"{safe}.html"


def fetch(url: str) -> str:
    path = cache_path(url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Codex F1 1:43 catalog photo discovery",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=25) as response:
        text = response.read().decode("utf-8", "replace")
    path.write_text(text, encoding="utf-8")
    time.sleep(0.15)
    return text


def compact_code(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).lower())


def image_candidates(page_url: str, text: str, catalog_number: str) -> list[str]:
    candidates: list[str] = []
    fullsize_links = re.findall(r'href=["\']([^"\']*/images/fullsize/[^"\']+\.jpg[^"\']*)["\']', text, flags=re.I)
    thumbnail_links = re.findall(r'src=["\']([^"\']*/images/big-thumbnails/[^"\']+\.jpg[^"\']*)["\']', text, flags=re.I)
    listing_links = re.findall(r'src=["\']([^"\']*/images/listing/[^"\']+\.jpg[^"\']*)["\']', text, flags=re.I)
    for url in [*fullsize_links, *thumbnail_links, *listing_links]:
        full = urljoin(page_url, html.unescape(clean(url)))
        if "[PRODUCT-PHOTO]" in full:
            continue
        if full not in candidates:
            candidates.append(full)
    patterns = [
        r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+(?:property|name)=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+(?:data-src|data-large-image|src)=["\']([^"\']+)["\'][^>]*(?:product|model|zoom|large|photo)',
        r'<img[^>]+(?:alt|title)=["\'][^"\']*(?:1:43|F1|Formula 1|Minichamps|Spark|Brumm|Ferrari|Williams|McLaren)[^"\']*["\'][^>]+(?:data-src|src)=["\']([^"\']+)["\']',
    ]
    code = compact_code(catalog_number)
    page_key = compact_code(page_url)
    page_is_specific = bool(code and code in page_key)
    if "raceland.eu" in page_url.lower() and re.search(r"/20-\d+", page_url):
        page_is_specific = True
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.I | re.S):
            url = html.unescape(clean(match))
            if not url or url.startswith("data:"):
                continue
            if re.search(r"\.(?:svg|gif)(?:\?|$)", url, flags=re.I):
                continue
            full = urljoin(page_url, url)
            image_key = compact_code(full)
            if code and not page_is_specific and code not in image_key:
                continue
            if full not in candidates:
                candidates.append(full)
    return candidates


def load_overrides() -> dict[str, object]:
    if not PHOTO_OVERRIDES.exists():
        return {}
    return json.loads(PHOTO_OVERRIDES.read_text(encoding="utf-8"))


def has_photo(value: object) -> bool:
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value.get("mainPhoto") or value.get("main") or value.get("thumbnails"))
    return False


def discover(season: str, limit: int) -> dict[str, int]:
    data = json.loads(APP_DATA.read_text(encoding="utf-8"))
    overrides = load_overrides()
    checked = 0
    found = 0
    failed = 0
    for model in data["models"]:
        if season != "all" and str(model.get("season")) != season:
            continue
        model_id = model["id"]
        if has_photo(overrides.get(model_id)):
            continue
        catalog_number = model.get("catalogNumber", "")
        urls = [url for url in model.get("sourceUrls", []) if not url.lower().endswith(".pdf")]
        if not urls:
            continue
        checked += 1
        if checked > limit:
            break
        for page_url in urls[:3]:
            try:
                text = fetch(page_url)
                images = image_candidates(page_url, text, catalog_number)
            except Exception:
                failed += 1
                continue
            if images:
                overrides[model_id] = {
                    "mainPhoto": images[0],
                    "thumbnails": images[1:6],
                    "originalPhotoUrl": images[0],
                    "sourcePageUrl": page_url,
                }
                PHOTO_OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
                found += 1
                break
    PHOTO_OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"checked": checked, "found": found, "failed": failed, "totalOverrides": len(overrides)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="1980")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()
    print(json.dumps(discover(args.season, args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
