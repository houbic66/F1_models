from __future__ import annotations

import re

from collect_model_catalog_expanded import fetch, strip_tags


def probe_replicarz():
    url = "https://www.replicarz.com/143-Minichamps-F1/products/3001/"
    text = fetch(url)
    print("replicarz productinfo", len(re.findall("productinfo", text, re.I)))
    print(re.findall(r'href=["\']([^"\']*productinfo[^"\']*)', text, re.I)[:30])
    print(re.findall(r'prodinfo\.asp\?number=([^"&<>]+)', text, re.I)[:30])


def probe_miniatures():
    url = "https://www.miniatures-minichamps.com/gb/17-f1-1990-a-1999"
    text = fetch(url)
    print("miniatures p", sorted(set(re.findall(r"[?&]p=(\d+)", text)))[:30])
    print("product-name", len(re.findall(r"product-name", text, re.I)))
    print(re.findall(r'<a[^>]+class="product-name[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.I | re.S)[:5])
    print(re.findall(r'href="([^"]+)"[^>]+class="product-name[^"]*"[^>]*>(.*?)</a>', text, re.I | re.S)[:5])


def probe_ck_root():
    for url in [
        "https://ck-modelcars.de/en/l/t-gesamt/k-formel1/",
        "https://ck-modelcars.de/en/l/t-gesamt/k-formel1/p-1/",
        "https://ck-modelcars.de/en/f1/",
    ]:
        text = fetch(url)
        titles = [strip_tags(m) for m in re.findall(r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>", text, re.I | re.S)]
        print("ck", url, len(text), len(titles), sum("1:43" in t for t in titles), titles[:8])
        print(sorted(set(re.findall(r"/en/l/t-gesamt/k-formel1[^\"']+", text)))[:20])


probe_replicarz()
probe_miniatures()
probe_ck_root()
