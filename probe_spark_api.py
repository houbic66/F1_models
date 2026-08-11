from __future__ import annotations

import json
import urllib.parse
import urllib.request


def api(params: dict) -> dict:
    url = "https://rapi.sparkmodel.com/products?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Content-Language": "en"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


params = {
    "q": "",
    "page_number": 1,
    "page_size": 5,
    "filters": json.dumps(['scale_name = "1:43"', 'category_ids = "Formula 1"']),
    "facets": json.dumps(["manufacturer_name", "scale_name", "brand_name", "model_name", "category_ids", "ranking_competition_name", "driver_names", "year"]),
}
for filter_variant in [
    [],
    ['scale_name = "1:43"', 'category_ids = "Formula 1"'],
    ['scale_name = "1:43"', 'ranking_competition_name = "Formula 1"'],
    ['scale_name = "1:43"', 'category_name = "Formula 1"'],
    ['scale_name = "1:43"'],
]:
    params["filters"] = json.dumps(filter_variant)
    print("\nfilters", filter_variant)
    try:
        data = api(params)
    except Exception as exc:
        print("ERROR", type(exc).__name__, exc)
        continue
    print(json.dumps(data.get("meta", {}), indent=2)[:2000])
    for row in data.get("data", [])[:3]:
        print(json.dumps(row, ensure_ascii=False)[:1200])
