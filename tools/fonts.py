#!/usr/bin/env python3
"""Скачивает шрифты сайта с Google Fonts в assets/fonts/, чтобы раздавать их со своего домена.

Пишет woff2-файлы и assets/fonts/fonts.json: какие @font-face к какому шрифту и набору символов относятся.
Перезапускать только при смене шрифтов или начертаний.
Запуск: python3 tools/fonts.py
"""
import json
import pathlib
import re
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / 'assets' / 'fonts'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'

# Ключ: под каким именем шрифт подключает build.py. Значение: параметр family для Google Fonts
FAMILIES = {
    'golos': 'Golos+Text:wght@400;500;600',
    'onest': 'Onest:wght@500;600;700',
    'mono': 'JetBrains+Mono:wght@500',
    'arabic': 'IBM+Plex+Sans+Arabic:wght@400;500;600;700',
    'rubik': 'Rubik:wght@400;500;600;700',
    'thai': 'Noto+Sans+Thai:wght@400;500;600;700',
}

# Наборы символов, которые нужны языкам сайта; остальные (греческий, вьетнамский и т.п.) не берём
SUBSETS = {'latin', 'latin-ext', 'cyrillic', 'cyrillic-ext', 'arabic', 'hebrew', 'thai'}


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30).read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, family in FAMILIES.items():
        css = get(f'https://fonts.googleapis.com/css2?family={family}&display=swap').decode()
        faces = []
        for subset, block in re.findall(r'/\* ([\w-]+) \*/\s*(@font-face\s*\{.*?\})', css, re.S):
            if subset not in SUBSETS:
                continue
            src = re.search(r'url\((https://[^)]+\.woff2)\)', block).group(1)
            weight = re.search(r'font-weight:\s*([\d ]+);', block).group(1).strip()
            name = f'{key}-{subset}-{weight.replace(" ", "-")}.woff2'
            if not (OUT / name).exists():
                (OUT / name).write_bytes(get(src))
            block = block.replace(src, f'/fonts/{name}')
            faces.append({'subset': subset, 'file': name, 'css': re.sub(r'\s+', ' ', block)})
        manifest[key] = faces
        print(key, len(faces), 'faces')
    (OUT / 'fonts.json').write_text(json.dumps(manifest, indent=1) + '\n')
    used = {f['file'] for faces in manifest.values() for f in faces}
    for old in OUT.glob('*.woff2'):
        if old.name not in used:
            old.unlink()
    total = sum(f.stat().st_size for f in OUT.glob('*.woff2'))
    print('ok', len(list(OUT.glob('*.woff2'))), 'files', total // 1024, 'K')


if __name__ == '__main__':
    main()
