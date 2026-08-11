from __future__ import annotations

import html
import json
import re
import time
import unicodedata
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from collect_model_catalog import ModelRow, clean, parse_model_line, split_car_and_type


OUT_DIR = Path("outputs") / "model_catalog"
CACHE_DIR = OUT_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MANUFACTURERS = [
    "Minichamps",
    "Spark",
    "Looksmart",
    "LookSmart",
    "Hot Wheels",
    "TSM",
    "TrueScale",
    "True Scale",
    "Quartzo",
    "Onyx",
    "Ebbro",
    "Brumm",
    "Bburago",
    "BBR",
    "GP Replicas",
    "Ixo",
    "IXO",
    "Altaya",
    "Panini",
    "DeAgostini",
    "Solido",
    "Edicola",
    "Tecnomodel",
    "Werk83",
    "CMR",
    "Ixo Collections",
]

NON_CAR_WORDS = re.compile(r"\b(helmet|helm|casque|figure|figurine|driver figure|pit crew|transporter|book|dvd|display|case|base|tyre set|tire set|welcome to|category|newsletter|1:5|1:2|1:8|1:12|1:18|1:20|1:24|1:64)\b", re.I)
NON_F1_WORDS = re.compile(r"\b(Indy|Indianapolis|Indycar|Formula 2|Formula 3|\bF2\b|\bF3\b|Rally|Le Mans|Super GT|GT3|GT500|MotoGP|NASCAR)\b", re.I)


def deaccent(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def cache_name(url: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:180]
    return CACHE_DIR / f"{safe}.html"


def fetch(url: str, sleep: float = 0.05) -> str:
    path = cache_name(url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 Codex F1 model catalog"})
    with urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", "replace")
    path.write_text(text, encoding="utf-8")
    time.sleep(sleep)
    return text


def strip_tags(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return clean(html.unescape(value))


def canonical_manufacturer(value: str) -> str:
    value = clean(value)
    aliases = {
        "LookSmart": "Looksmart",
        "True Scale": "TSM",
        "TrueScale": "TSM",
        "Ixo": "IXO",
        "Ixo Collections": "IXO",
    }
    return aliases.get(value, value)


def find_manufacturer(text: str) -> str:
    for m in MANUFACTURERS:
        if re.search(rf"\b{re.escape(m)}\b", text, flags=re.I):
            return canonical_manufacturer(m)
    slug = unquote(urlparse(text).path).lower()
    for m in MANUFACTURERS:
        if re.search(rf"\b{re.escape(m.lower().replace(' ', '-'))}\b", slug):
            return canonical_manufacturer(m)
    return ""


def year_from(text: str) -> str:
    match = re.search(r"\b(19\d{2}|20[0-3]\d)\b", text)
    return match.group(1) if match else ""


def number_from(text: str) -> str:
    match = re.search(r"(?:#|No\.?|Nr\.?)\s*([0-9]{1,3}[A-Z]?)\b", text, flags=re.I)
    return match.group(1) if match else ""


def code_from_title(title: str, manufacturer: str) -> str:
    patterns = [
        r"\b(S\d{3,5}[A-Z]?|SF\d{2,4}|Y\d{3,5}|5HF\d{2,5}|18S\d{3,5}|43[A-Z0-9]{3,}|LSF\d{3,5}|LSRC\d{3,5}|LS18F\d{3,5}|BBR\d+[A-Z0-9]*|GP43[-A-Z0-9]+|TSM\d{5,}|R\d{3}[A-Z]?|P\d{9}|PMA\d{6,})\b",
        r"\b(4\d{8,9}|5\d{8,9}|53\d{7,9}|43\d{7,9})\b",
    ]
    for pat in patterns:
        match = re.search(pat, title, flags=re.I)
        if match:
            return match.group(1)
    return ""


def title_from_slug(url: str) -> str:
    path = unquote(urlparse(url).path).strip("/")
    if not path:
        return ""
    parts = path.split("/")
    if "productinfo" in [p.lower() for p in parts]:
        idx = [p.lower() for p in parts].index("productinfo")
        slug = parts[idx - 1] if idx > 0 else parts[-1]
    else:
        slug = parts[-1]
        if slug.startswith("p-") and len(parts) > 1:
            slug = parts[-2]
    slug = re.sub(r"\.(?:aspx|html?)$", "", slug, flags=re.I)
    slug = slug.replace("-", " ")
    return clean(slug)


def row_from_title(title: str, url: str, source_name: str, manufacturer: str = "", code: str = "", scale: str = "1/43") -> ModelRow | None:
    title = clean(title)
    if not title or NON_CAR_WORDS.search(title):
        return None
    if re.match(r"^F1\s+(?:19|20)\d{2}\s*\D+\s*(?:19|20)\d{2}$", title, flags=re.I):
        return None
    if NON_F1_WORDS.search(title):
        return None
    if not re.search(r"\b(?:Formula 1|F1|Grand Prix|GP)\b", title, flags=re.I):
        # Keep historic car-only source titles when they still look like known F1 constructors/types.
        if not re.search(r"\b(Ferrari|McLaren|Williams|Lotus|Brabham|Tyrrell|Benetton|Jordan|Minardi|Ligier|Arrows|BRM|Cooper|Vanwall|Wolf|March|Surtees|Hesketh|Alfa Romeo|Mercedes|Red Bull|Renault|Brawn|Sauber|Aston Martin|Alpine|Haas|Toro Rosso|Alpha Tauri)\b", title, flags=re.I):
            return None
    manufacturer = manufacturer or find_manufacturer(title) or find_manufacturer(url)
    code = code or code_from_title(title, manufacturer)
    year = year_from(title)
    if year and int(year) < 1950:
        return None
    number = number_from(title)
    title_work = re.sub(r"\b1[:/ -]?43(?:rd| scale)?\b", " ", title, flags=re.I)
    title_work = re.sub(r"\bFormula 1\b|\bF1\b|\bmodel car\b|\bscale model\b", " ", title_work, flags=re.I)
    title_work = re.sub(r"\b" + re.escape(manufacturer) + r"\b", " ", title_work, flags=re.I) if manufacturer else title_work
    title_work = re.sub(r"\b" + re.escape(code) + r"\b", " ", title_work, flags=re.I) if code else title_work
    constructor_car, chassis_type = split_car_and_type(clean(title_work.split(str(year))[0] if year else title_work))
    return ModelRow(
        year=year,
        constructor_car=constructor_car,
        chassis_type=chassis_type,
        driver="",
        car_number=number,
        team_livery="",
        race_gp_version=clean(title),
        manufacturer=manufacturer,
        model_code=code,
        scale=scale,
        source_url=url,
        source_name=source_name,
        raw_title=title,
    )


def collect_ck() -> list[ModelRow]:
    rows: list[ModelRow] = []
    urls = ["https://ck-modelcars.de/en/f1/", "https://ck-modelcars.de/en/l/t-gesamt/k-formel1/"]
    urls.extend(f"https://ck-modelcars.de/en/l/t-gesamt/k-formel1/a-18/p-{page}/" for page in range(1, 80))
    for url in urls:
        try:
            text = fetch(url)
        except Exception as exc:
            print("warn ck", url, exc)
            continue
        matches = re.findall(r'<h2[^>]*>\s*<a\s+href="([^"]+/p-\d+/)"[^>]*>\s*(.*?)\s*</a>', text, flags=re.I | re.S)
        for href, body in matches:
            full = urljoin(url, html.unescape(href))
            title = strip_tags(body)
            if "1:43" not in title or NON_CAR_WORDS.search(title):
                continue
            row = row_from_title(title, full, "CK-Modelcars Formula 1 category")
            if row:
                rows.append(row)
    return rows


def collect_diecastlegends() -> list[ModelRow]:
    rows: list[ModelRow] = []
    for page in range(1, 40):
        url = f"https://www.diecastlegends.com/f1-models?Scale=1-43&listing_page={page}"
        try:
            text = fetch(url)
        except Exception as exc:
            print("warn diecast", url, exc)
            break
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]*(?:1-43|1:43)[^<]*)</a>', text, flags=re.I)
        if not links:
            links = [(href, title_from_slug(href)) for href in re.findall(r'href="([^"]*(?:1-43|1:43)[^"]*model-car[^"]*)"', text, flags=re.I)]
        seen_page = 0
        for href, title in links:
            full = urljoin(url, html.unescape(href))
            title = strip_tags(title) or title_from_slug(full)
            row = row_from_title(title, full, "Diecast Legends F1 1:43")
            if row:
                rows.append(row)
                seen_page += 1
        if page > 1 and seen_page == 0:
            break
    return rows


def collect_raceland() -> list[ModelRow]:
    rows: list[ModelRow] = []
    urls = [
        "https://raceland.eu/motorsports/formula-1/",
        "https://raceland.eu/motorsports/formula-1/preview/",
        "https://raceland.eu/motorsports/formula-1/preview/massstab-1-43/",
        "https://raceland.eu/motorsports/formula-1/new-in-stock/",
        "https://raceland.eu/SOLD-OUT",
    ]
    try:
        main = fetch("https://raceland.eu/motorsports/formula-1/")
        urls.extend(sorted(set(urljoin("https://raceland.eu/motorsports/formula-1/", h) for h in re.findall(r'href="([^"]*/motorsports/formula-1/[^"]*)"', main, flags=re.I))))
    except Exception:
        pass
    for url in sorted(set(urls)):
        try:
            text = fetch(url)
        except Exception as exc:
            print("warn raceland", url, exc)
            continue
        for match in re.finditer(r'<a href="([^"]+)"\s+title="([^"]+)"\s+class="product-name stretched-link">', text, flags=re.I):
            full = urljoin(url, html.unescape(match.group(1)))
            title = clean(html.unescape(match.group(2)))
            block = text[match.end() : match.end() + 2200]
            scale = ""
            scale_match = re.search(r"Scale\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", block, flags=re.I)
            if not scale_match:
                scale_match = re.search(r"Scale\s+([0-9:]+)", strip_tags(block), flags=re.I)
            if scale_match:
                scale = clean(scale_match.group(1))
            if scale and scale != "1:43":
                continue
            if not scale and "massstab-1-43" not in url and "1:43" not in strip_tags(block)[:600]:
                continue
            manufacturer = ""
            man_match = re.search(r"Manufacturer\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", block, flags=re.I)
            if man_match:
                manufacturer = canonical_manufacturer(strip_tags(man_match.group(1)))
            code = ""
            code_match = re.search(r"Product number\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", block, flags=re.I)
            if code_match:
                code = strip_tags(code_match.group(1))
            row = row_from_title(title, full, "Raceland Formula 1 pages", manufacturer=manufacturer, code=code, scale="1/43")
            if row:
                driver_match = re.search(r"Driver name\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", block, flags=re.I)
                if driver_match:
                    row.driver = strip_tags(driver_match.group(1))
                rows.append(row)
    return rows


def collect_replicarz() -> list[ModelRow]:
    rows: list[ModelRow] = []
    category_urls = [
        "https://www.replicarz.com/143-Minichamps-F1/products/3001/",
        "https://www.replicarz.com/143-2021-F1/products/2299/",
        "https://www.replicarz.com/143-2022-F1/products/2721/",
        "https://www.replicarz.com/143-2023-F1/products/2863/",
        "https://www.replicarz.com/143-2024-F1/products/3042/",
        "https://www.replicarz.com/143-2025-F1/products/3280/",
        "https://www.replicarz.com/143-2026-F1/products/3517/",
        "https://www.replicarz.com/143-Spark-Classic-F1/products/3581/",
        "https://www.replicarz.com/143-Spark-2026-F1/products/3582/",
        "https://www.replicarz.com/143-Looksmart/products/3056/",
    ]
    for url in category_urls:
        try:
            text = fetch(url)
        except Exception as exc:
            print("warn replicarz", url, exc)
            continue
        for href in sorted(set(re.findall(r'href="([^"]*productinfo/[^"]+/?)"', text, flags=re.I))):
            full = urljoin(url, html.unescape(href))
            title = title_from_slug(full)
            code = clean(urlparse(full).path.strip("/").split("/")[-1])
            row = row_from_title(title, full, "Replicarz F1 categories", code=code)
            if row:
                rows.append(row)
    return rows


def collect_miniatures_minichamps() -> list[ModelRow]:
    rows: list[ModelRow] = []
    base_categories = [
        "https://www.miniatures-minichamps.com/gb/13-f1-2025",
        "https://www.miniatures-minichamps.com/gb/15-f1-2010-2020",
        "https://www.miniatures-minichamps.com/gb/16-f1-2000-2009",
        "https://www.miniatures-minichamps.com/gb/17-f1-1990-a-1999",
    ]
    categories = []
    for base in base_categories:
        categories.append(base)
        try:
            text = fetch(base)
            pages = sorted({int(p) for p in re.findall(r"[?&]p=(\d+)", text)})
            categories.extend(f"{base}?p={p}" for p in pages if p > 1)
        except Exception:
            pass
    for url in categories:
        try:
            text = fetch(url)
        except Exception as exc:
            print("warn miniatures", url, exc)
            continue
        for href, title in re.findall(r'<a[^>]+href="([^"]+)"[^>]+title="([^"]*(?:F1|Formula 1|GP)[^"]*)"', text, flags=re.I):
            full = urljoin(url, html.unescape(href))
            title = clean(html.unescape(title))
            if "1/43" not in title and "1:43" not in title:
                nearby = text[max(0, text.find(href) - 1200) : text.find(href) + 2200]
                if "1/43" not in nearby and "1:43" not in nearby:
                    continue
            row = row_from_title(title, full, "Miniatures-Minichamps F1 categories")
            if row:
                rows.append(row)
    return rows


def collect_grandprixmodels() -> list[ModelRow]:
    rows: list[ModelRow] = []
    endpoint = "https://www.grandprixmodels.com/_Processing/_Product-Search.aspx"
    scale_143 = "b977fd3d-f21e-4cc1-9a36-75f7cbdd89f9~"
    formula_event = "b8b7221c-c9e0-46ff-a65b-4541fb1d4fa4~"
    model_product_types = "2d774889-0856-4f32-9853-91076d31719b~0a29a36f-0ada-4ca9-b640-49c8db57d976~c80b0f08-d01d-4fb6-bdc4-517344beca20~"
    for page in range(1, 250):
        data = urlencode(
            {
                "action": "search",
                "scales": scale_143,
                "events": formula_event,
                "producttypes": model_product_types,
                "availability": "",
                "brands": "",
                "keywords": "",
                "pagenumber": str(page),
                "order": "name",
                "specialReportType": "",
            }
        ).encode()
        cache_url = f"{endpoint}?f1_143_page={page}"
        try:
            path = cache_name(cache_url).with_suffix(".json")
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            else:
                req = Request(
                    endpoint,
                    data=data,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                )
                with urlopen(req, timeout=60) as resp:
                    payload = json.loads(resp.read().decode("utf-8", "replace"))
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                time.sleep(0.05)
        except Exception as exc:
            print("warn grandprixmodels", page, exc)
            continue
        results = payload.get("results") or []
        if not results:
            break
        for item in results:
            title = clean(item.get("productname", ""))
            if NON_CAR_WORDS.search(title):
                continue
            full = urljoin("https://www.grandprixmodels.com/", item.get("producturl", ""))
            manufacturer = canonical_manufacturer(clean(item.get("brandnameastext", "")))
            code = clean(item.get("sku", ""))
            row = row_from_title(title, full, "Grand Prix Models Formula 1 1:43 JSON", manufacturer=manufacturer, code=code)
            if row:
                row.year = clean(item.get("dates", "")) or row.year
                row.driver = strip_tags(item.get("drivers", ""))
                row.scale = clean(item.get("scalesastext", "")) or "1:43"
                row.race_gp_version = clean(item.get("eventsastext", "")) or row.race_gp_version
                rows.append(row)
        total_pages = int(payload.get("totalPages") or page)
        if page >= total_pages:
            break
    return rows


def collect_ebay() -> list[ModelRow]:
    rows: list[ModelRow] = []
    queries = [
        "Spark 1/43 F1",
        "Minichamps 1/43 Formula 1",
        "Looksmart 1/43 F1",
        "Onyx 1/43 F1",
        "Quartzo 1/43 F1",
        "Hot Wheels 1/43 Ferrari F1",
        "TSM 1/43 F1",
        "Ebbro 1/43 F1",
    ]
    for q in queries:
        for page in range(1, 8):
            url = "https://www.ebay.com/sch/i.html?" + "&".join(
                [
                    "_nkw=" + q.replace(" ", "+"),
                    "_sacat=180270",
                    "_pgn=" + str(page),
                ]
            )
            try:
                text = fetch(url, sleep=0.2)
            except Exception as exc:
                print("warn ebay", q, page, exc)
                break
            titles = re.findall(r'class="s-item__title[^"]*"[^>]*>(.*?)</', text, flags=re.I | re.S)
            if not titles:
                break
            for title in titles:
                title = strip_tags(title)
                if "1/43" not in title and "1:43" not in title:
                    continue
                row = row_from_title(title, url, "eBay search results")
                if row:
                    rows.append(row)
    return rows


def load_existing() -> list[ModelRow]:
    raw = json.loads((OUT_DIR / "sourced_model_catalog_raw.json").read_text(encoding="utf-8"))
    return [ModelRow(**row) for row in raw]


def dedupe(rows: list[ModelRow]) -> list[ModelRow]:
    by_key: dict[str, ModelRow] = {}
    for row in rows:
        code = re.sub(r"[^a-z0-9]", "", deaccent(clean(row.model_code)).lower())
        title_key = re.sub(r"[^a-z0-9]+", " ", deaccent(clean(row.raw_title)).lower()).strip()
        if code and row.manufacturer:
            key = f"code|{row.manufacturer.lower()}|{code}"
        else:
            key = f"title|{title_key}"
        if key not in by_key:
            by_key[key] = row
        else:
            old = by_key[key]
            sources = set(filter(None, old.source_name.split(" | "))) | {row.source_name}
            old.source_name = " | ".join(sorted(sources))
            urls = set(filter(None, old.source_url.split(" | "))) | {row.source_url}
            old.source_url = " | ".join(sorted(urls))[:3000]
            if not old.driver and row.driver:
                old.driver = row.driver
            if not old.model_code and row.model_code:
                old.model_code = row.model_code
            if not old.manufacturer and row.manufacturer:
                old.manufacturer = row.manufacturer
    final = list(by_key.values())
    final.sort(key=lambda r: (r.year or "9999", r.constructor_car, r.chassis_type, r.driver, r.manufacturer, r.model_code, r.raw_title))
    return final


def main() -> None:
    collectors = [
        ("existing", load_existing),
        ("ck", collect_ck),
        ("diecastlegends", collect_diecastlegends),
        ("raceland", collect_raceland),
        ("replicarz", collect_replicarz),
        ("miniatures_minichamps", collect_miniatures_minichamps),
        ("grandprixmodels", collect_grandprixmodels),
        ("ebay", collect_ebay),
    ]
    all_rows: list[ModelRow] = []
    source_counts: dict[str, int] = {}
    for name, func in collectors:
        rows = func()
        source_counts[name] = len(rows)
        print(name, len(rows))
        all_rows.extend(rows)
    final = dedupe(all_rows)
    out_json = OUT_DIR / "sourced_model_catalog_expanded_raw.json"
    out_csv = OUT_DIR / "sourced_model_catalog_expanded_raw.csv"
    out_json.write_text(json.dumps([asdict(row) for row in final], ensure_ascii=False, indent=2), encoding="utf-8")
    import csv

    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(final[0]).keys()))
        writer.writeheader()
        for row in final:
            writer.writerow(asdict(row))
    counts: dict[str, int] = {}
    for row in final:
        counts[row.manufacturer or "(unknown)"] = counts.get(row.manufacturer or "(unknown)", 0) + 1
    summary = {"source_raw_counts": source_counts, "total_before_dedupe": len(all_rows), "total_after_dedupe": len(final), "by_manufacturer": dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))}
    (OUT_DIR / "sourced_model_catalog_expanded_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
