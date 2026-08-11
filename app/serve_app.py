from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 4173


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    os.chdir(APP_DIR)
    server = ThreadingHTTPServer((HOST, PORT), QuietHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
