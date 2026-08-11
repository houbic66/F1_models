from __future__ import annotations

import urllib.request


req = urllib.request.Request("https://www.sparkmodel.com/main-5LXJACXW.js", headers={"User-Agent": "Mozilla/5.0"})
js = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
for pos in [510500, 534000, 540500, 544000, 558000]:
    print("\n---", pos, "---")
    print(js[pos : pos + 3500])
