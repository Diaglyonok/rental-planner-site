#!/usr/bin/env python3
"""Берёт локализованные скриншоты для сторов из realtor-manage-app и кладёт уменьшенные WebP в assets/shots/<lang>/.

Источник: tool/aso/out/iphone/screenshots/<lang>/*.png (генерируются ASO-скриптами приложения).
Скриншоты, в подписи которых (tool/aso/texts/<lang>.json) есть длинное тире, на сайт не берутся.
Нужен cwebp (brew install webp). Перезапускать после обновления скриншотов в сторах.
Запуск: python3 tools/shots.py [путь к realtor-manage-app]
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

OUT = HERE / 'assets' / 'shots'
WIDTH = 720


def main() -> None:
    app = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'realtor-manage-app'
    src = app / 'tool' / 'aso' / 'out' / 'iphone' / 'screenshots'
    cwebp = shutil.which('cwebp')
    if not cwebp:
        raise SystemExit('нужен cwebp: brew install webp')
    if OUT.exists():
        shutil.rmtree(OUT)
    for lang in build.LANGS:
        (OUT / lang).mkdir(parents=True)
        cards = json.loads((app / 'tool' / 'aso' / 'texts' / f'{lang}.json').read_text()).get('cards', {})
        taken = []
        for name in build.SHOTS:
            if re.search('[\u2014\u2013]', json.dumps(cards.get(name, {}), ensure_ascii=False)):
                continue
            taken.append(name)
            png = src / lang / f'{name}.png'
            out = OUT / lang / f'{name}.webp'
            subprocess.run([cwebp, '-quiet', '-q', '80', '-resize', str(WIDTH), '0', str(png), '-o', str(out)], check=True)
        print(lang, ', '.join(taken))
    total = sum(f.stat().st_size for f in OUT.rglob('*.webp'))
    print('ok', total // 1024, 'K')


if __name__ == '__main__':
    main()
