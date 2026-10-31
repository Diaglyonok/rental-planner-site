#!/usr/bin/env python3
"""Сообщает поисковикам с поддержкой IndexNow (Bing, Яндекс и другие) обо всех адресах из dist/sitemap.xml.

Запускать после деплоя, когда сайт уже отдаёт новую версию и файл ключа <INDEXNOW_KEY>.txt в корне.
Запуск: python3 tools/indexnow.py
"""
import json
import pathlib
import re
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402


def main() -> None:
    sitemap = (build.DIST / 'sitemap.xml').read_text()
    urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
    host = build.SITE.split('://', 1)[1]
    body = json.dumps({
        'host': host,
        'key': build.INDEXNOW_KEY,
        'keyLocation': f'{build.SITE}/{build.INDEXNOW_KEY}.txt',
        'urlList': urls,
    }).encode()
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.status, len(urls), 'адресов отправлено')


if __name__ == '__main__':
    main()
