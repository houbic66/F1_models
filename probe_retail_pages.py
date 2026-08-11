from __future__ import annotations

import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch(url: str) -> str:
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


urls = [
    "https://raceland.eu/motorsports/formula-1/",
    "https://raceland.eu/motorsports/formula-1/preview/massstab-1-43/",
    "https://www.diecastlegends.com/f1-models?Scale=1-43&listing_page=1",
    "https://www.replicarz.com/143-Minichamps-F1/products/3001/",
    "https://www.grandprixmodels.com/Search.aspx?keywords=formula+1+1%3A43&order=orderByName&selected=&stock=showALL",
    "https://www.miniatures-minichamps.com/gb/17-f1-1990-a-1999",
]
for url in urls:
    print("\nURL", url)
    html = fetch(url)
    print("length", len(html))
    print("titles", re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, flags=re.I | re.S)[:20])
    hrefs = sorted(set(urljoin(url, h) for h in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I)))
    for h in hrefs[:160]:
        if any(x in h.lower() for x in ["formula", "f1", "143", "1-43", "page", "products", "search", "scale"]):
            print(h)
