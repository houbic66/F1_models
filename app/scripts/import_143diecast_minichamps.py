from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "app" / "data" / "photo_page_cache"
RAW_CATALOG = ROOT / "outputs" / "model_catalog" / "sourced_model_catalog_expanded_raw.json"
PHOTO_OVERRIDES = ROOT / "app" / "data" / "model_photo_overrides.json"
BASE_URL = "http://www.143diecastmodels.co.uk/"


TEAM_FILES = {
    "arrows": "http_www_143diecastmodels_co_uk_arrows_html.html",
    "brabham": "http_www_143diecastmodels_co_uk_brabham_html.html",
    "ferrari": "http_www_143diecastmodels_co_uk_ferrari_html.html",
    "hardtofind": "http_www_143diecastmodels_co_uk_hardtofind_html.html",
    "ligier": "http_www_143diecastmodels_co_uk_ligier_html.html",
    "mclaren": "http_www_143diecastmodels_co_uk_mclaren_html.html",
    "williams": "http_www_143diecastmodels_co_uk_williams_html.html",
    "wolf": "http_www_143diecastmodels_co_uk_wolf_html.html",
    "tyrrell": "http_www_143diecastmodels_co_uk_tyrrell_html.html",
    "lotus": "http_www_143diecastmodels_co_uk_lotus_html.html",
}


def clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def compact_code(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


def year_from_minichamps_code(code: str) -> str:
    compact = compact_code(code)
    if not re.fullmatch(r"\d{9}", compact):
        return ""
    year = int(compact[3:5])
    return str(1900 + year if year >= 50 else 2000 + year)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", clean(value).lower()).strip("-")


def model_id(code: str) -> str:
    return f"minichamps__{slug(compact_code(code))}"


def parse_title(title: str, team: str, code: str) -> dict[str, str]:
    title = clean(title)
    title = re.sub(r"^\d{3}\s*\d{6}\s*", "", title)
    title = re.sub(r"\s*\(.*?\)\s*", " ", title)
    title = clean(title)
    parts = [clean(part) for part in re.split(r"\s+-\s+", title) if clean(part)]
    model = parts[0] if parts else title
    rest = parts[1:] if len(parts) > 1 else []
    driver = rest[-1] if rest else ""
    event = " - ".join(rest[:-1])
    if driver and not re.match(r"^[A-Z]\.", driver):
        event = " - ".join(rest)
        driver = ""
    if team == "mclaren" and model == "McLaren MP4":
        model = "McLaren MP4/1"
    if team == "lotus" and model == "Lotus" and year_from_minichamps_code(code) == "1979":
        model = "Lotus 79"
    constructor, chassis = model, ""
    model_parts = model.split()
    for idx, part in enumerate(model_parts):
        if re.search(r"\d", part) and idx > 0:
            constructor = " ".join(model_parts[:idx])
            chassis = " ".join(model_parts[idx:])
            break
    if not chassis:
        constructor = team.capitalize() if team != "mclaren" else "McLaren"
        chassis = model.replace(constructor, "").strip() or model
    return {
        "year": year_from_minichamps_code(code),
        "constructor_car": constructor,
        "chassis_type": chassis,
        "driver": driver,
        "car_number": "",
        "team_livery": "",
        "race_gp_version": event,
    }


def load_existing() -> list[dict[str, str]]:
    return json.loads(RAW_CATALOG.read_text(encoding="utf-8"))


def main() -> None:
    raw = load_existing()
    existing = {
        (
            clean(row.get("source_name")),
            compact_code(row.get("model_code", "")),
            clean(row.get("source_url")),
        )
        for row in raw
    }
    overrides = json.loads(PHOTO_OVERRIDES.read_text(encoding="utf-8"))
    added_rows = 0
    added_photos = 0
    for team, filename in TEAM_FILES.items():
        path = CACHE_DIR / filename
        if not path.exists():
            continue
        source_url = urljoin(BASE_URL, f"{team}.html")
        text = path.read_text(encoding="utf-8", errors="replace")
        for href, title in re.findall(
            r'<a\s+href="([^"]+)"[^>]+title="([^"]+)"[^>]*>\s*<img',
            text,
            flags=re.I | re.S,
        ):
            title = clean(title)
            code_match = re.match(r"^(\d{3}\s*\d{6})\b", title)
            if not code_match:
                continue
            code = compact_code(code_match.group(1))
            year = year_from_minichamps_code(code)
            if not year:
                continue
            row_bits = parse_title(title, team, code)
            row = {
                **row_bits,
                "manufacturer": "Minichamps",
                "model_code": code,
                "scale": "1/43",
                "source_url": source_url,
                "source_name": "143diecastmodels Minichamps pages",
                "raw_title": title,
                "limited_edition": "",
                "price_aud": "",
                "notes": "Parsed from 143diecastmodels team gallery",
            }
            key = (row["source_name"], row["model_code"], row["source_url"])
            if key not in existing:
                raw.append(row)
                existing.add(key)
                added_rows += 1
            photo_url = urljoin(source_url, html.unescape(href))
            photo_key = model_id(code)
            current = overrides.get(photo_key)
            if not (isinstance(current, dict) and (current.get("mainPhoto") or current.get("main"))):
                overrides[photo_key] = {
                    "mainPhoto": photo_url,
                    "thumbnails": [],
                    "originalPhotoUrl": photo_url,
                    "sourcePageUrl": source_url,
                }
                added_photos += 1
    RAW_CATALOG.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    PHOTO_OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rowsAdded": added_rows, "photosAdded": added_photos}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
