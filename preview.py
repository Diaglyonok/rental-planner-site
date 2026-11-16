#!/usr/bin/env python3
"""Собирает сайт и раздаёт dist/ на http://localhost:8000 (порт можно передать аргументом)."""
import functools
import http.server
import io
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    """Как на хостинге: /terms отдаёт terms.html, несуществующий адрес отдаёт ближайший 404.html."""

    def send_head(self):
        path = pathlib.Path(self.translate_path(self.path))
        if not path.exists() and path.with_suffix('.html').is_file():
            self.path = self.path.split('?')[0] + '.html'
        elif not path.exists():
            page = self.nearest_404(path)
            if page:
                body = page.read_bytes()
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                return io.BytesIO(body)
        return super().send_head()

    def nearest_404(self, path: pathlib.Path):
        root = pathlib.Path(self.directory)
        for folder in (path.parent, *path.parent.parents):
            if (folder / '404.html').is_file():
                return folder / '404.html'
            if folder == root:
                return None
        return None


def main() -> None:
    subprocess.run([sys.executable, str(HERE / 'build.py')], check=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = functools.partial(Handler, directory=str(HERE / 'dist'))
    print(f'http://localhost:{port}')
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()


if __name__ == '__main__':
    main()
