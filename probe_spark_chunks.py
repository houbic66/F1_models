from __future__ import annotations

import re
from urllib.request import Request, urlopen


def fetch(path: str) -> str:
    with urlopen(Request("https://www.sparkmodel.com/" + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


chunks = ["chunk-CInGXy4G.js", "chunk-BnqoHsdq.js", "chunk-C7kwRTu7.js", "chunk-DMLEu1DT.js"]
for ch in chunks:
    js = fetch(ch)
    print("\n", ch, len(js))
    for term in ["products", "product", "category", "page", "limit", "apiURL", "ranking"]:
        print(term, [m.start() for m in re.finditer(term, js, re.I)][:20])
    for pos in [m.start() for m in re.finditer("apiURL|products|categories|competitions", js, re.I)][:12]:
        print("\n---", pos, "---")
        print(js[max(0, pos - 800) : pos + 1600])
