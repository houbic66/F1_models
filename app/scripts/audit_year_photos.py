from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
APP_DATA = ROOT / "app" / "data" / "app-data.json"
OUT_ROOT = ROOT / "outputs" / "year_runs"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_image(url: str) -> dict[str, Any]:
    if not clean(url):
        return {
            "photoStatus": "missing",
            "photoHttpStatus": "",
            "photoContentType": "",
            "photoCheckedAt": now_iso(),
            "photoError": "",
        }
    if url.lower().endswith(".pdf"):
        return {
            "photoStatus": "not_image",
            "photoHttpStatus": "",
            "photoContentType": "application/pdf",
            "photoCheckedAt": now_iso(),
            "photoError": "PDF is not an image",
        }
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Codex F1 photo audit",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            content_type = clean(response.headers.get("content-type", "")).split(";", 1)[0].lower()
            status = int(response.status)
            if status == 200 and content_type.startswith("image/"):
                photo_status = "verified"
            elif status in {401, 403}:
                photo_status = "blocked"
            else:
                photo_status = "not_image"
            return {
                "photoStatus": photo_status,
                "photoHttpStatus": status,
                "photoContentType": content_type,
                "photoCheckedAt": now_iso(),
                "photoError": "",
            }
    except HTTPError as exc:
        return {
            "photoStatus": "blocked" if exc.code in {401, 403} else "error",
            "photoHttpStatus": exc.code,
            "photoContentType": clean(exc.headers.get("content-type", "")).split(";", 1)[0].lower(),
            "photoCheckedAt": now_iso(),
            "photoError": str(exc),
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "photoStatus": "error",
            "photoHttpStatus": "",
            "photoContentType": "",
            "photoCheckedAt": now_iso(),
            "photoError": str(exc),
        }


def audit(season: str, limit: int = 0) -> dict[str, Any]:
    data = json.loads(APP_DATA.read_text(encoding="utf-8"))
    rows = [row for row in data.get("models", []) if season == "all" or str(row.get("season")) == season]
    if limit > 0:
        rows = rows[:limit]

    details: list[dict[str, Any]] = []
    by_manufacturer: dict[str, Counter] = defaultdict(Counter)
    for idx, model in enumerate(rows, start=1):
        result = check_image(clean(model.get("mainPhoto")))
        maker = clean(model.get("manufacturer")) or "(unknown)"
        by_manufacturer[maker][result["photoStatus"]] += 1
        details.append(
            {
                "id": model.get("id", ""),
                "season": model.get("season", ""),
                "manufacturer": maker,
                "catalogNumber": model.get("catalogNumber", ""),
                "title": model.get("title", ""),
                "mainPhoto": model.get("mainPhoto", ""),
                "sourceUrls": model.get("sourceUrls", []),
                **result,
            }
        )
        if idx % 25 == 0:
            time.sleep(0.1)

    summary = {
        "season": season,
        "checkedAt": now_iso(),
        "total": len(details),
        "byStatus": dict(Counter(row["photoStatus"] for row in details)),
        "byManufacturer": {maker: dict(counter) for maker, counter in sorted(by_manufacturer.items())},
        "problemRows": [
            row
            for row in details
            if row["photoStatus"] != "verified"
        ],
    }

    out_dir = OUT_ROOT / str(season)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "photo_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "photo_audit_problem_rows.json").write_text(
        json.dumps(summary["problemRows"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="1982")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    summary = audit(args.season, args.limit)
    print(json.dumps({key: value for key, value in summary.items() if key != "problemRows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
