from __future__ import annotations

import json
import urllib.parse
import urllib.request


def search(q: str, filters: list[str] | None = None) -> dict:
    params = {
        "q": q,
        "page_number": 1,
        "page_size": 8,
        "filters": json.dumps(filters or []),
        "facets": json.dumps(["manufacturer_name", "scale_name", "category_ids", "ranking_competition_name", "year"]),
    }
    url = "https://rapi.sparkmodel.com/products?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Content-Language": "en"})
    return json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace"))


for q in ["Formula 1", "F1", "Grand Prix", "McLaren", "Ferrari", "Mercedes", "Red Bull", "Lotus"]:
    data = search(q, ['scale_name = "1:43"'])
    print("\n", q, data.get("meta", {}).get("total_hits"))
    print(json.dumps(data.get("meta", {}).get("facet_distribution", {}), indent=2)[:1000])
    for r in data.get("data", []):
        print(r.get("code"), r.get("scale_name"), r.get("year"), r.get("name", "").replace("\n", " ")[:160])
