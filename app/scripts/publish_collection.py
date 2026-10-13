from __future__ import annotations

import argparse
import ctypes
import getpass
import json
import os
import sys
import time
from pathlib import Path
from ctypes import wintypes
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "http://62.238.50.166/api"
TOKEN_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "F1_models" / "admin-token.dpapi"
WORKBOOK_NAME = "Diecast 2026.xlsx"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def dpapi_transform(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise OSError("Ukládání tokenu přes Windows DPAPI je dostupné pouze ve Windows.")

    source_buffer = ctypes.create_string_buffer(data)
    source = DATA_BLOB(
        len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    result = DATA_BLOB()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if protect:
        transform = crypt32.CryptProtectData
        transform.argtypes = [
            ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
        ]
    else:
        transform = crypt32.CryptUnprotectData
        transform.argtypes = [
            ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
        ]
    transform.restype = wintypes.BOOL
    extra = (
        ["F1 Models admin token", None, None, None, 0]
        if protect
        else [None, None, None, None, 0]
    )
    if not transform(ctypes.byref(source), *extra, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(result.pbData)


def configure_token() -> None:
    token = getpass.getpass("Admin token (vstup se nezobrazuje): ").strip()
    if not token:
        raise ValueError("Token nebyl zadán.")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    encrypted = dpapi_transform(token.encode("utf-16-le"), protect=True)
    TOKEN_FILE.write_text(encrypted.hex(), encoding="ascii")
    token = ""
    print("Admin token je uložen zašifrovaný pro tento účet Windows.")


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise FileNotFoundError("Token chybí. Nejdřív spusťte tento skript s --configure.")
    try:
        encrypted = bytes.fromhex(TOKEN_FILE.read_text(encoding="ascii").strip())
        return dpapi_transform(encrypted, protect=False).decode("utf-16-le")
    except (ValueError, OSError, UnicodeError):
        raise RuntimeError("Token se nepodařilo načíst. Spusťte znovu --configure pod svým účtem Windows.")


def find_workbook() -> Path:
    candidates: list[Path] = []
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "Dokumenty" / WORKBOOK_NAME)
    candidates.append(Path.home() / "OneDrive" / "Dokumenty" / WORKBOOK_NAME)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Soubor {WORKBOOK_NAME} nebyl nalezen. Zkoušené cesty:\n{tried}")


def api_json(path: str, token: str) -> dict:
    request = Request(f"{API_BASE}{path}", headers={"X-Admin-Token": token})
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            message = json.loads(body).get("error", f"HTTP {exc.code}")
        except json.JSONDecodeError:
            message = f"HTTP {exc.code}"
        raise RuntimeError(message) from exc
    except URLError as exc:
        raise RuntimeError(f"Aplikace není dostupná: {exc.reason}") from exc


def publish(workbook: Path) -> None:
    workbook = workbook.expanduser().resolve()
    if workbook.name.lower() != WORKBOOK_NAME.lower() and not workbook.name.lower().endswith(".xlsx"):
        raise ValueError("Zdrojový soubor musí být Excel .xlsx.")
    if not workbook.is_file():
        raise FileNotFoundError(f"Soubor nenalezen: {workbook}")
    if workbook.stat().st_size > 15 * 1024 * 1024:
        raise ValueError("Excel je větší než povolených 15 MB.")

    token = load_token()
    body = workbook.read_bytes()
    request = Request(
        f"{API_BASE}/collection/update",
        data=body,
        method="POST",
        headers={
            "X-Admin-Token": token,
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            job = json.loads(response.read().decode("utf-8"))["job"]
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            message = json.loads(detail).get("error", f"HTTP {exc.code}")
        except json.JSONDecodeError:
            message = f"HTTP {exc.code}"
        raise RuntimeError(message) from exc
    finally:
        token = ""
        body = b""

    job_id = job["id"]
    print(f"Excel nahrán; přepočítávám sbírku (úloha {job_id}).")
    while True:
        current = api_json(f"/jobs/{job_id}", "")
        job = current.get("job", {})
        status = job.get("status", "")
        if status == "done":
            summary = job.get("summary", {})
            print(
                "Hotovo: "
                f"{summary.get('collectionRows', 0)} řádků sbírky, "
                f"{summary.get('masterModels', 0)} modelů v katalogu."
            )
            return
        if status == "failed":
            raise RuntimeError(job.get("error") or "Přepočet sbírky selhal.")
        print(f"Probíhá: {job.get('step') or status}…")
        time.sleep(4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Přímé načtení OneDrive sbírky do aplikace F1 Models.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--configure", action="store_true", help="Jednorázově uloží admin token zašifrovaný přes Windows DPAPI.")
    action.add_argument("--publish", action="store_true", help="Načte aktuální OneDrive Excel a přepočítá cloudovou aplikaci.")
    parser.add_argument("--workbook", type=Path, help="Volitelná cesta k jinému XLSX souboru.")
    args = parser.parse_args()
    try:
        if args.configure:
            configure_token()
        else:
            publish(args.workbook or find_workbook())
        return 0
    except Exception as exc:
        print(f"Chyba: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
