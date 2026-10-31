#!/usr/bin/env python3
"""Собирает сайт и раздаёт dist/ на http://localhost:8000 (порт можно передать аргументом)."""
import functools
import http.server
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    """Как на хостинге: /terms отдаёт terms.html."""

    def send_head(self):
        path = pathlib.Path(self.translate_path(self.path))
        if not path.exists() and path.with_suffix('.html').is_file():
            self.path = self.path.split('?')[0] + '.html'
        return super().send_head()


def main() -> None:
    subprocess.run([sys.executable, str(HERE / 'build.py')], check=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = functools.partial(Handler, directory=str(HERE / 'dist'))
    print(f'http://localhost:{port}')
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()


if __name__ == '__main__':
    main()
