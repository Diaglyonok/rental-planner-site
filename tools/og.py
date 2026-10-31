#!/usr/bin/env python3
"""Снимает картинки для соцсетей (og:image, 1200×630) с хиро каждой языковой версии в assets/og/.

Нужен Google Chrome. Перезапускать после правок хиро или его текстов.
Запуск: python3 tools/og.py
"""
import functools
import http.server
import pathlib
import shutil
import subprocess
import sys
import threading

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
OUT = HERE / 'assets' / 'og'


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def main() -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium') or CHROME
    build.main(require_og=False)
    handler = functools.partial(QuietHandler, directory=str(build.DIST))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for lang in build.LANGS:
            url = f'http://127.0.0.1:{server.server_port}{build.page_path(lang)}'
            out = OUT / f'{lang}.png'
            subprocess.run([
                chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-prefers-reduced-motion',
                '--force-device-scale-factor=1', '--window-size=1200,630', '--virtual-time-budget=6000',
                f'--screenshot={out}', url,
            ], check=True, capture_output=True)
            print(lang, out.relative_to(HERE))
    finally:
        server.shutdown()
    build.main()


if __name__ == '__main__':
    main()
