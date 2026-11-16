"""Минимальный Markdown в HTML для постов блога, без зависимостей.

Поддерживает то, что пишет редактор Sveltia CMS: заголовки, абзацы, списки, цитаты, картинки,
ссылки, жирный и курсив, код, горизонтальную линию. Сырой HTML экранируется.
"""
import html
import re

# Размер картинки по её адресу: (ширина, высота) или None. build.py подставляет свою функцию,
# чтобы у картинок были width и height и страница не прыгала при загрузке
image_size = lambda src: None


def img(src: str, alt: str) -> str:
    size = image_size(src)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ''
    return f'<img src="{src}" alt="{alt}"{dims} loading="lazy">'


def front_matter(text: str) -> tuple:
    """Разбирает YAML-шапку из простых пар ключ: значение. Возвращает (поля, тело)."""
    m = re.match(r'---\s*\n(.*?)\n---\s*\n?(.*)', text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        km = re.match(r'([\w-]+):\s*(.*?)\s*(#.*)?$', line)
        if not km:
            continue
        value = km.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1].replace('\\"', '"')
        meta[km.group(1)] = value
    return meta, m.group(2)


def inline(s: str) -> str:
    codes = []

    def keep_code(m):
        codes.append(f'<code>{html.escape(m.group(1))}</code>')
        return f'\x00{len(codes) - 1}\x00'
    s = re.sub(r'`([^`]+)`', keep_code, s)
    s = html.escape(s, quote=False)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)',
               lambda m: img(m.group(2), m.group(1)), s)

    def link(m):
        href = m.group(2)
        ext = href.startswith('http') and 'rentalplanner.io' not in href
        return f'<a href="{href}"' + (' target="_blank" rel="noopener"' if ext else '') + f'>{m.group(1)}</a>'
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, s)
    s = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda m: f'<strong>{m.group(1) or m.group(2)}</strong>', s)
    s = re.sub(r'(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])|(?<![_\w])_(?!\s)(.+?)(?<!\s)_(?![_\w])',
               lambda m: f'<em>{m.group(1) or m.group(2)}</em>', s)
    return re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], s)


def to_html(text: str) -> str:
    out, para, items, kind, quote = [], [], [], None, []

    def flush():
        nonlocal kind
        if para:
            joined = ' '.join(para)
            img = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+)\)', joined.strip())
            out.append(f'<figure>{inline(joined)}</figure>' if img else f'<p>{inline(joined)}</p>')
            para.clear()
        if items:
            out.append(f'<{kind}>' + ''.join(f'<li>{inline(i)}</li>' for i in items) + f'</{kind}>')
            items.clear()
            kind = None
        if quote:
            out.append(f'<blockquote>{to_html(chr(10).join(quote))}</blockquote>')
            quote.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if line.startswith('>'):
            if para or items:
                flush()
            quote.append(line[1:].lstrip())
            continue
        if quote:
            flush()
        h = re.match(r'(#{1,6})\s+(.*)', line)
        ul = re.match(r'\s*[-*+]\s+(.*)', line)
        ol = re.match(r'\s*\d+[.)]\s+(.*)', line)
        if h:
            flush()
            level = max(2, len(h.group(1)))
            out.append(f'<h{level}>{inline(h.group(2).strip())}</h{level}>')
        elif re.fullmatch(r'\s*([-*_])(\s*\1){2,}\s*', line):
            flush()
            out.append('<hr>')
        elif ul or ol:
            new = 'ul' if ul else 'ol'
            if para or (kind and kind != new):
                flush()
            kind = new
            items.append((ul or ol).group(1))
        elif items and raw.startswith(('  ', '\t')):
            items[-1] += ' ' + line.strip()
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return '\n'.join(out)
