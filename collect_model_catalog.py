from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from pypdf import PdfReader


OUT_DIR = Path("outputs") / "model_catalog"
OUT_DIR.mkdir(parents=True, exist_ok=True)

F1SCALE_PDF_URL = "https://www.f1scalemodels.com/F1_Stocklist.pdf"
F1SCALE_PDF = OUT_DIR / "F1_Stocklist.pdf"
F1SCALE_TXT = OUT_DIR / "F1_Stocklist.txt"
MINICHAMPS_HOME = "http://www.143diecastmodels.co.uk/"
LOOKSMART_TAG_URL = "https://looksmartmodels.com/product-tag/formula-1/"

MANUFACTURERS = [
    "Minichamps",
    "Spark",
    "Looksmart",
    "Hot Wheels",
    "TSM",
    "Quartzo",
    "Onyx",
    "Ebbro",
    "Brumm",
    "Bburago",
    "BBR",
    "GP Replicas",
    "Ixo",
    "Altaya",
    "Panini",
    "DeAgostini",
    "Solido",
    "Edicola",
    "IXO",
]


@dataclass
class ModelRow:
    year: str
    constructor_car: str
    chassis_type: str
    driver: str
    car_number: str
    team_livery: str
    race_gp_version: str
    manufacturer: str
    model_code: str
    scale: str
    source_url: str
    source_name: str
    raw_title: str
    limited_edition: str = ""
    price_aud: str = ""
    notes: str = ""


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 Codex catalog builder"})
    try:
        with urlopen(req, timeout=45) as resp:
            return resp.read()
    except Exception:
        if url.startswith("https://"):
            fallback = "http://" + url.removeprefix("https://")
            req = Request(fallback, headers={"User-Agent": "Mozilla/5.0 Codex catalog builder"})
            with urlopen(req, timeout=45) as resp:
                return resp.read()
        raise


def clean(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def deaccent(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def find_manufacturer(line: str) -> tuple[str, int, int] | None:
    candidates = []
    for m in MANUFACTURERS:
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(m)}(?![A-Za-z])", re.I)
        match = pattern.search(line)
        if match:
            candidates.append((match.start(), match.end(), m))
    if not candidates:
        return None
    start, end, m = sorted(candidates, key=lambda item: item[0])[-1]
    canonical = "IXO" if m.upper() == "IXO" else m
    return canonical, start, end


def parse_driver_number(text: str) -> tuple[str, str]:
    match = re.search(r"([A-Z]\.[A-Za-zÀ-ž' -]+?)\s*\(([^)]+)\)", text)
    if not match:
        return "", ""
    return clean(match.group(1)), clean(match.group(2))


def split_car_and_type(prefix: str) -> tuple[str, str]:
    prefix = clean(re.sub(r"^\bR\b\s+", "", prefix))
    tokens = prefix.split()
    if not tokens:
        return "", ""
    type_idx = None
    for i, token in enumerate(tokens):
        if re.search(r"\d", token) and i > 0:
            type_idx = i
            break
    if type_idx is None:
        return prefix, ""
    return clean(" ".join(tokens[:type_idx])), clean(" ".join(tokens[type_idx:]))


def parse_model_line(line: str, source_url: str, source_name: str) -> ModelRow | None:
    line = clean(line)
    if not line or line.startswith(("Updated ", "Model Year ", "Edition ", "Price ", "Formula 1", "Page ")):
        return None
    if "F o r m u l a" in line:
        line = clean(line.replace("F o r m u l a 1 , 2 a n d 3", ""))
    if not re.search(r"\b(19|20)\d{2}\b", line):
        return None
    man = find_manufacturer(line)
    if not man:
        return None
    manufacturer, man_start, man_end = man
    before_man = clean(line[:man_start])
    after_man = clean(line[man_end:])
    year_match = re.search(r"\b(19|20)\d{2}\b", before_man)
    if not year_match:
        return None
    year = year_match.group(0)
    prefix = clean(before_man[: year_match.start()])
    description = clean(before_man[year_match.end() :])

    code = ""
    limited = ""
    price = ""
    tail_tokens = after_man.split()
    if tail_tokens:
        if len(tail_tokens) == 1 and re.fullmatch(r"\d+(?:\.\d{2})?", tail_tokens[0]):
            rest = tail_tokens
        elif re.match(r"^[A-Z]?[A-Z0-9][A-Z0-9./-]*[A-Z0-9]$", tail_tokens[0], re.I):
            code = tail_tokens[0]
            rest = tail_tokens[1:]
        else:
            rest = tail_tokens
        if rest and re.fullmatch(r"\d{2,6}", rest[0]):
            limited = rest[0]
            rest = rest[1:]
        if rest and re.fullmatch(r"\d+(?:\.\d{2})?", rest[-1]):
            price = rest[-1]

    driver, car_number = parse_driver_number(description)
    race = description
    if driver:
        race = clean(description[description.find("(") + len(car_number) + 2 :])
    constructor_car, chassis_type = split_car_and_type(prefix)
    if int(year) < 1950:
        return None
    return ModelRow(
        year=year,
        constructor_car=constructor_car,
        chassis_type=chassis_type,
        driver=driver,
        car_number=car_number,
        team_livery="",
        race_gp_version=race,
        manufacturer=manufacturer,
        model_code=code,
        scale="1/43",
        source_url=source_url,
        source_name=source_name,
        raw_title=line,
        limited_edition=limited,
        price_aud=price,
    )


def extract_f1scale() -> list[ModelRow]:
    F1SCALE_PDF.write_bytes(fetch_bytes(F1SCALE_PDF_URL))
    reader = PdfReader(str(F1SCALE_PDF))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        lines.extend(text.splitlines())
    F1SCALE_TXT.write_text("\n".join(lines), encoding="utf-8")
    rows = []
    for line in lines:
        row = parse_model_line(line, F1SCALE_PDF_URL, "F1 Scale Models stock list")
        if row:
            rows.append(row)
    return rows


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href")
            if href:
                self.links.append(href)

    def handle_data(self, data):
        text = clean(data)
        if text:
            self.text_parts.append(text)


def fetch_text(url: str) -> tuple[str, list[str]]:
    html = fetch_bytes(url).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(html)
    return "\n".join(parser.text_parts), parser.links


def minichamps_pages() -> list[str]:
    text, links = fetch_text(MINICHAMPS_HOME)
    urls = {MINICHAMPS_HOME}
    for href in links:
        full = urljoin(MINICHAMPS_HOME, href)
        parsed = urlparse(full)
        if parsed.netloc == "www.143diecastmodels.co.uk" and parsed.path.endswith(".html"):
            urls.add(full)
    return sorted(urls)


def parse_143_pages() -> list[ModelRow]:
    rows: list[ModelRow] = []
    pages = minichamps_pages()
    (OUT_DIR / "143diecastmodels_pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")
    for url in pages:
        try:
            text, _links = fetch_text(url)
        except Exception as exc:
            print(f"warn: failed {url}: {exc}")
            continue
        parts = [clean(part) for part in text.splitlines() if clean(part)]
        for idx, part in enumerate(parts):
            if not re.search(r"\bCode:\s*", part, re.I):
                continue
            prev = " ".join(parts[max(0, idx - 3) : idx + 1])
            prev = clean(prev)
            code_match = re.search(r"\bCode:\s*([A-Z0-9 ]{3,20})", prev, re.I)
            if not code_match:
                continue
            code = clean(code_match.group(1))
            title = clean(prev[: code_match.start()])
            year_match = re.search(r"\b(19|20)\d{2}\b", title)
            year = year_match.group(0) if year_match else ""
            driver = ""
            # Most pages end title with a compact initial+surname driver.
            driver_match = re.search(r"\b([A-Z]\.[A-Za-zÀ-ž' -]+)\s*(?:Est\. Value|L/E|$)", title)
            if driver_match:
                driver = clean(driver_match.group(1))
            title_no_driver = clean(title.replace(driver, "")) if driver else title
            constructor_car, chassis_type = split_car_and_type(title_no_driver)
            if not title or not code:
                continue
            rows.append(
                ModelRow(
                    year=year,
                    constructor_car=constructor_car,
                    chassis_type=chassis_type,
                    driver=driver,
                    car_number="",
                    team_livery="",
                    race_gp_version="",
                    manufacturer="Minichamps",
                    model_code=code,
                    scale="1/43",
                    source_url=url,
                    source_name="143diecastmodels Minichamps pages",
                    raw_title=title,
                )
            )
    return rows


def parse_looksmart_title(title: str) -> tuple[str, str, str, str, str]:
    title = clean(title.replace("–", "-"))
    title = re.sub(r"\s+1:43$", "", title)
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    year = year_match.group(0) if year_match else ""
    chunks = [clean(x) for x in title.split(" - ") if clean(x)]
    car = chunks[0] if chunks else title
    driver = ""
    version_parts: list[str] = []
    known_drivers = [
        "Lewis Hamilton",
        "Charles Leclerc",
        "Carlos Sainz",
        "Sebastian Vettel",
        "Kimi Raikkonen",
        "Fernando Alonso",
        "Michael Schumacher",
        "Felipe Massa",
    ]
    for chunk in chunks[1:]:
        if any(name.lower() in chunk.lower() for name in known_drivers):
            driver = chunk
        else:
            version_parts.append(chunk)
    if not driver and len(chunks) >= 2:
        driver = chunks[-1]
        version_parts = chunks[1:-1]
    constructor_car, chassis_type = split_car_and_type(car)
    return year, constructor_car, chassis_type, driver, clean(" ".join(version_parts))


def parse_looksmart_pages() -> list[ModelRow]:
    rows: list[ModelRow] = []
    for page in range(1, 12):
        url = LOOKSMART_TAG_URL if page == 1 else urljoin(LOOKSMART_TAG_URL, f"page/{page}/")
        try:
            text, _links = fetch_text(url)
        except Exception as exc:
            print(f"warn: failed {url}: {exc}")
            break
        parts = [clean(part) for part in text.splitlines() if clean(part)]
        page_rows = 0
        for idx, part in enumerate(parts):
            if part == "Product Code" and idx + 1 < len(parts):
                code = clean(parts[idx + 1].lstrip(":"))
            elif part.startswith("Product Code:"):
                code = clean(part.split(":", 1)[1])
            else:
                continue
            if not code.upper().startswith("LSF"):
                continue
            title = ""
            for back in range(idx - 1, max(-1, idx - 8), -1):
                if "1:43" in parts[back] and not parts[back].startswith(("Quick View", "Showing ")):
                    title = parts[back]
                    break
            if not title:
                continue
            year, constructor_car, chassis_type, driver, version = parse_looksmart_title(title)
            rows.append(
                ModelRow(
                    year=year,
                    constructor_car=constructor_car,
                    chassis_type=chassis_type,
                    driver=driver,
                    car_number="",
                    team_livery="Race Livery",
                    race_gp_version=version,
                    manufacturer="Looksmart",
                    model_code=code,
                    scale="1/43",
                    source_url=url,
                    source_name="Looksmart Formula 1 tag",
                    raw_title=title,
                )
            )
            page_rows += 1
        if page_rows == 0:
            break
    return rows


def row_key(row: ModelRow) -> str:
    bits = [row.manufacturer, row.model_code, row.year, row.raw_title]
    return deaccent(clean("|".join(bits))).lower()


def main() -> None:
    rows: list[ModelRow] = []
    rows.extend(extract_f1scale())
    rows.extend(parse_143_pages())
    rows.extend(parse_looksmart_pages())
    deduped: dict[str, ModelRow] = {}
    for row in rows:
        key = row_key(row)
        if key not in deduped:
            deduped[key] = row
    final_rows = list(deduped.values())
    final_rows.sort(key=lambda r: (r.year or "9999", r.constructor_car, r.chassis_type, r.driver, r.manufacturer, r.model_code))
    json_path = OUT_DIR / "sourced_model_catalog_raw.json"
    csv_path = OUT_DIR / "sourced_model_catalog_raw.csv"
    json_path.write_text(json.dumps([asdict(r) for r in final_rows], ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(final_rows[0]).keys()))
        writer.writeheader()
        for row in final_rows:
            writer.writerow(asdict(row))
    counts: dict[str, int] = {}
    for row in final_rows:
        counts[row.manufacturer] = counts.get(row.manufacturer, 0) + 1
    print("rows", len(final_rows))
    print(json.dumps(dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
