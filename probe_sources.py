from __future__ import annotations

import re
from urllib.request import Request, urlopen


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 Codex source probe"})
    with urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", "replace")


for url in [
    "https://ck-modelcars.de/en/l/t-gesamt/k-formel1/a-18/",
    "https://www.sparkmodel.com/products/ff9c1233-4444-4657-b5ad-215800937c1e",
    "https://www.sparkmodel.com/",
]:
    print("\nURL", url)
    html = fetch(url)
    print("length", len(html))
    hrefs = sorted(set(re.findall(r'href="([^"]+)"', html)))
    print("hrefs", hrefs[:120])
    print("api-ish", sorted(set(re.findall(r"(?:https?:)?//[^\"'<> ]*api[^\"'<> ]*|api\.[^\"'<> ]+|/api/[^\"'<> ]+", html)))[:120])
    print("assets", sorted(set(re.findall(r'src="([^"]+\.(?:js|mjs))"', html)))[:30])

print("\nSpark JS")
js = fetch("https://www.sparkmodel.com/main-5LXJACXW.js")
print("length", len(js))
for term in ["products", "categories", "api.sparkmodel", "search", "reference"]:
    print("term", term, [m.start() for m in re.finditer(term, js, flags=re.I)][:20])
for match in re.finditer(r"(?:https?:)?//api\.sparkmodel\.com[^\"'` ]*|['\"](/[^'\"\s]{3,100})['\"]", js):
    print(match.group(0)[:180])
