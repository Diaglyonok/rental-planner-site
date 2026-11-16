#!/usr/bin/env python3
"""Собирает сайт в dist/: отдельная статичная страница на каждый язык, плюс файлы для поисковиков.

Английская версия лежит в корне (/), остальные в /<lang>/. Тексты, цены и числа вшиваются
в HTML при сборке, чтобы поисковики и AI-краулеры видели страницу без выполнения JS.

Запуск: python3 build.py
"""
import datetime
import html
import json
import math
import pathlib
import re
import shutil

import mdlite

HERE = pathlib.Path(__file__).resolve().parent
SVG = HERE / 'assets' / 'icons'
DIST = HERE / 'dist'

SITE = 'https://www.rentalplanner.io'
EMAIL = 'info@dglfactor.tech'
APP_STORE = 'https://apps.apple.com/app/id1631552064'
APP_STORE_RU = 'https://apps.apple.com/ru/app/id1631552064'
GOOGLE_PLAY = 'https://play.google.com/store/apps/details?id=com.github.diaglyonok.realtor_manage_app'
WEB_APP = 'https://app.rentalplanner.io'
TG_CHANNEL = 'https://t.me/rentalplanner'
TG_BOT = 'https://t.me/rental_planner_bot?start=contact'
API_DOCS = 'https://rp-api.dglfactor.tech/docs/rental-planner-api'

RATING, RATING_COUNT = 4.9, 350

ICONS = {
    'home': 'home_field.svg',
    'car': 'car_field.svg',
    'boat': 'boat_field.svg',
    'pets': 'pets_field.svg',
    'tools': 'tools_field.svg',
    'bike': 'bikes_field.svg',
    'tg': 'telegram_icon.svg',
    'wa': 'whatsapp_icon.svg',
}

LANGS = ['ru', 'en', 'de', 'es', 'fr', 'pt', 'tr', 'ar', 'he', 'th']
ROOT_LANG = 'en'
X_DEFAULT = 'en'
RTL = {'ar', 'he'}
CIS = ['uk', 'be', 'kk', 'ky', 'uz', 'hy', 'ka', 'az', 'tg']
OG_LOCALE = {
    'ru': 'ru_RU', 'en': 'en_US', 'de': 'de_DE', 'es': 'es_ES', 'fr': 'fr_FR',
    'pt': 'pt_BR', 'tr': 'tr_TR', 'ar': 'ar_AR', 'he': 'he_IL', 'th': 'th_TH',
}

# Шрифты лежат в assets/fonts (скачиваются tools/fonts.py) и раздаются со своего домена
FONTS = ['golos', 'onest', 'mono']
EXTRA_FONTS = {'ar': 'arabic', 'he': 'rubik', 'th': 'thai'}

# Скриншоты из сторов (assets/shots/<lang>/, обновляются tools/shots.py)
SHOTS = ['01_calendar', '02_stats', '03_expenses', '04_notifications', '05_units', '06_details']

# Аналитика: подставь токен Cloudflare Web Analytics и/или номер счётчика Яндекс.Метрики (только для ru)
CF_ANALYTICS_TOKEN = ''
YANDEX_METRIKA_ID = ''

# Ключ IndexNow: файл <ключ>.txt кладётся в корень, tools/indexnow.py сообщает Bing и Яндексу об обновлениях
INDEXNOW_KEY = 'ebc4a9de6378bada077e8f3a979f6ebe'

# Цены тарифов: ru в рублях, остальные в USD витрины USA из App Store. [месяц, год]
PRICES = {
    'rub': {'free': [0, 0], 'basic': [199, 1240], 'premium': [399, 2490], 'business': [1990, 11990]},
    'usd': {'free': [0, 0], 'basic': [3.49, 22.49], 'premium': [6.99, 44.99], 'business': [29.99, 179.99]},
}
RUB_PER_USD = 90

# Как Intl.NumberFormat форматирует числа в браузере: разделитель тысяч, десятичный знак,
# минимум цифр для группировки и обрамление суммы в валюте (narrowSymbol)
NUM = {
    'ru': ('\u00a0', ',', 1, '', '\u00a0\u20bd'),
    'en': (',', '.', 1, '$', ''),
    'de': ('.', ',', 1, '', '\u00a0$'),
    'es': ('.', ',', 2, '', '\u00a0$'),
    'fr': ('\u202f', ',', 1, '', '\u00a0$'),
    'pt': ('.', ',', 1, '$\u00a0', ''),
    'tr': ('.', ',', 1, '$', ''),
    'ar': (',', '.', 1, '\u200f', '\u00a0US$'),
    'he': (',', '.', 1, '\u200f', '\u00a0\u200f$'),
    'th': (',', '.', 1, '$', ''),
}

JS_KEYS = ['h1', 'words', 'labels', 'notes', 'units', 'guests', 'msgs']
DOMAINS = ['flats', 'houses', 'glamp', 'cars', 'boats', 'yachts', 'pets', 'tools', 'bikes']

# Юридические страницы только на английском: legal/<name>.html вставляется в шаблон legal/page.html
LEGAL = {
    'terms': 'Terms of use for Rental Planner, its subscriptions, payments and accounts.',
    'privacy': 'How Rental Planner collects, uses, shares and protects your personal information.',
}

# Старые адреса сайта на Wix (он был на русском), чтобы не потерять их позиции в поиске
REDIRECTS = [
    ('/bookingcalendar', '/ru/vacation-rental-software/'),
    ('/autorent', '/ru/car-rental-software/'),
    ('/pethotels', '/ru/pet-hotel-software/'),
    ('/payment-management', '/ru/'),
    ('/data-sync', '/ru/'),
    ('/часто-задаваемые-вопросы', '/ru/#faq'),
    ('/blog', '/ru/blog/'),
    ('/post/как-избежать-двойное-бронирование-в-посуточной-аренде', '/ru/blog/kak-izbezhat-dvojnogo-bronirovaniya/'),
    ('/post/10-советов-арендодателю', '/ru/blog/10-sovetov-arendodatelyu/'),
    ('/post/организация-аренды-с-помощью-цифрового-планировщика-аренды', '/ru/blog/cifrovoj-planirovshhik-arendy/'),
    ('/post/*', '/ru/blog/'),
]

# Страницы сфер: тексты в spheres/<lang>.json, адрес /<lang>/<slug>/, скриншоты из SHOTS (первый в хиро)
SPHERES = {
    'flats': {'slug': 'vacation-rental-software', 'icon': 'home', 'shots': ['01_calendar', '04_notifications', '03_expenses', '02_stats']},
    'cars': {'slug': 'car-rental-software', 'icon': 'car', 'shots': ['01_calendar', '06_details', '04_notifications', '03_expenses']},
    'boats': {'slug': 'boat-rental-software', 'icon': 'boat', 'shots': ['01_calendar', '06_details', '02_stats', '04_notifications']},
    'pets': {'slug': 'pet-hotel-software', 'icon': 'pets', 'shots': ['05_units', '01_calendar', '04_notifications', '02_stats']},
    'tools': {'slug': 'equipment-rental-software', 'icon': 'tools', 'shots': ['05_units', '01_calendar', '03_expenses', '02_stats']},
    'bikes': {'slug': 'bike-rental-software', 'icon': 'bike', 'shots': ['01_calendar', '04_notifications', '02_stats', '03_expenses']},
}
SHOT_SIZE = (720, 1560)
EN_MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def symbol(name: str, file: str) -> str:
    raw = (SVG / file).read_text()
    view_box = re.search(r'viewBox="([^"]+)"', raw).group(1)
    inner = re.search(r'<svg[^>]*>(.*)</svg>', raw, re.S).group(1)
    inner = re.sub(r'\s(fill)="(?!none)[^"]*"', '', inner)
    inner = re.sub(r'\s(id|data-name)="[^"]*"', '', inner)
    inner = re.sub(r'\s+', ' ', inner).strip()
    return f'<symbol id="i-{name}" viewBox="{view_box}" fill="currentColor">{inner}</symbol>'


FALLBACK_SQUIGGLE = '''<svg class="squiggle" viewBox="-60 -60 1940 2120" aria-hidden="true">
  <defs>
    <linearGradient id="sqGrad" gradientUnits="userSpaceOnUse" x1="0" y1="900" x2="1814" y2="1300">
      <stop offset="0" stop-color="#BFF0F4"/><stop offset=".2" stop-color="#36D1DC"/><stop offset=".46" stop-color="#5B86E5"/>
      <stop offset=".72" stop-color="#36D1DC"/><stop offset="1" stop-color="#22408F"/>
    </linearGradient>
  </defs>
  <path class="draw" pathLength="1" d="M95 1560 L1250 165 L165 1845 L1495 600 L765 1785 L1665 1095 L1300 1880" fill="none" stroke="url(#sqGrad)" stroke-width="270" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''


def squiggle() -> str:
    custom = HERE / 'assets' / 'squiggle.svg'
    if not custom.exists():
        return FALLBACK_SQUIGGLE
    raw = re.sub(r'<\?xml[^>]*>', '', custom.read_text()).strip()
    return re.sub(r'<svg', '<svg class="squiggle" aria-hidden="true"', raw, count=1)


def extract_ru(html_src: str) -> dict:
    d = {}
    for m in re.finditer(r'<(\w+)\b[^>]*?\sdata-i="([^"]+)"[^>]*>(.*?)</\1>', html_src, re.S):
        d[m.group(2)] = m.group(3).strip()
    for m in re.finditer(r'data-ia="([^"]+)"\s+aria-label="([^"]*)"', html_src):
        d[m.group(1)] = m.group(2)
    return d


def check_locale(lang: str, data: dict, ref: dict) -> list:
    errs = [f'{lang}: нет ключа {k}' for k in ref if k != '_js' and k not in data]
    js = data.get('_js', {})
    errs += [f'{lang}: нет _js.{k}' for k in JS_KEYS if k not in js]
    if 'words' in js:
        keys = {w[1] for w in js['words']}
        errs += [f'{lang}: words без домена {d}' for d in DOMAINS if d not in keys]
    for part in ('labels', 'notes', 'guests'):
        errs += [f'{lang}: _js.{part} без {d}' for d in DOMAINS if d not in js.get(part, {})]
    for d, names in js.get('units', {}).items():
        if len(names) != 6:
            errs.append(f'{lang}: _js.units.{d} должно быть 6 объектов')
    for d, names in js.get('guests', {}).items():
        if len(names) < 12:
            errs.append(f'{lang}: _js.guests.{d} меньше 12 имён')
    text = json.dumps(data, ensure_ascii=False)
    for bad in ('\u2014', '\u2013'):
        if bad in text:
            errs.append(f'{lang}: запрещённое тире {bad!r}')
    return errs


def load_locales(src: str) -> dict:
    ru = extract_ru(src)
    ru.update(json.loads((HERE / 'i18n' / 'ru.json').read_text()))
    out, errs = {'ru': ru}, []
    for lang in LANGS[1:]:
        data = json.loads((HERE / 'i18n' / f'{lang}.json').read_text())
        errs += check_locale(lang, data, ru)
        out[lang] = data
    if errs:
        raise SystemExit('\n'.join(errs))
    return out


# Числа и деньги так же, как их рисует JS страницы

def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def fmt(lang: str, v: float, decimals: int = 0) -> str:
    group, dec, min_group = NUM[lang][:3]
    whole, _, frac = f'{abs(v):.{decimals}f}'.partition('.')
    if len(whole) > 3 and len(whole) >= 3 + min_group:
        head = len(whole) % 3 or 3
        whole = whole[:head] + ''.join(group + whole[i:i + 3] for i in range(head, len(whole), 3))
    return ('-' if v < 0 else '') + whole + (dec + frac if frac else '')


def to_local(lang: str, rub: float) -> float:
    return rub if lang == 'ru' else js_round(rub / RUB_PER_USD)


def money(lang: str, rub: float, raw: bool = False, cents: bool = False) -> str:
    v = rub if raw else to_local(lang, rub)
    pre, post = NUM[lang][3:]
    return pre + fmt(lang, v, 2 if cents else 0) + post


def fill(lang: str, s: str) -> str:
    return re.sub(r'\{m:(\d+)\}', lambda m: money(lang, int(m.group(1))), s)


def plain(lang: str, s: str) -> str:
    """Текст без разметки: для meta, JSON-LD и llms.txt."""
    return html.unescape(re.sub(r'<[^>]+>', ' ', fill(lang, s))).replace('\u00a0', ' ').replace('  ', ' ').strip()


def attr(s: str) -> str:
    return html.escape(html.unescape(s), quote=True)


def page_url(lang: str) -> str:
    return f'{SITE}/' if lang == ROOT_LANG else f'{SITE}/{lang}/'


def page_path(lang: str) -> str:
    return '/' if lang == ROOT_LANG else f'/{lang}/'


def page_file(lang: str) -> str:
    return 'index.html' if lang == ROOT_LANG else f'{lang}/index.html'


# Пререндер страницы

def sub_one(pattern: str, repl, s: str, flags: int = 0) -> str:
    out, n = re.subn(pattern, repl, s, count=1, flags=flags)
    if not n:
        raise SystemExit(f'Не найден фрагмент для пререндера: {pattern}')
    return out


def prerender(src: str, lang: str, all_t: dict, blog_langs: set) -> str:
    t, j = all_t[lang], all_t[lang]['_js']
    s = re.sub(r'%%SPHERE:(\w+)%%', lambda m: sphere_path(lang, m.group(1)), src)
    if lang in blog_langs:
        s = s.replace('<li data-blog><a href="%%BLOG%%"', f'<li><a href="{blog_path(lang)}"')
    else:
        s = re.sub(r'\n\s*<li data-blog>.*?</li>', '', s)

    def texts(m):
        tag, key, inner = m.group(1), m.group(2), m.group(3)
        v = t.get(key)
        if v is None:
            return m.group(0)
        v = fill(lang, v)
        if tag in ('text', 'tspan'):
            v = html.escape(html.unescape(v), quote=False)
        open_tag = m.group(0)[:m.group(0).index('>') + 1]
        return f'{open_tag}{v}</{tag}>'

    s = re.sub(r'<(\w+)\b[^>]*?\sdata-i="([^"]+)"[^>]*>(.*?)</\1>', texts, s, flags=re.S)
    s = re.sub(r'(data-ia="([^"]+)"\s+aria-label=")[^"]*"',
               lambda m: m.group(1) + attr(t.get(m.group(2), '')) + '"', s)

    s = re.sub(r'(<b data-m="(\d+)"(?: data-mp="([^"]*)")?>)[^<]*',
               lambda m: m.group(1) + (m.group(3) or '') + money(lang, int(m.group(2))), s)
    s = re.sub(r'(<span class="rb-(?:got|exp)"[^>]*data-n="(\d+)">)[^<]*',
               lambda m: m.group(1) + fmt(lang, to_local(lang, int(m.group(2)))), s)
    s = re.sub(r'(<b data-count="(\d+)"(?: data-prefix="([^"]*)")?>)[^<]*',
               lambda m: m.group(1) + (m.group(3) or '') + fmt(lang, to_local(lang, int(m.group(2)))), s)

    def counter(m):
        n, k, plus = int(m.group(2)), m.group(3), m.group(4)
        v = fmt(lang, js_round(n / 1000)) + 'K' if k else fmt(lang, n)
        return m.group(1) + v + ('+' if plus else '')
    s = re.sub(r'(<b class="cnt" data-num="(\d+)"( data-k="1")?( data-plus="1")?>)[^<]*', counter, s)
    s = sub_one(r'(<b id="ratingV">)[^<]*', lambda m: m.group(1) + fmt(lang, RATING, 1), s)

    table = PRICES['rub' if lang == 'ru' else 'usd']
    s = re.sub(r'(<div class="price" data-plan="(\w+)"><b>)[^<]*',
               lambda m: m.group(1) + money(lang, table[m.group(2)][0], raw=True,
                                            cents=lang != 'ru' and table[m.group(2)][0] % 1 != 0), s)

    # Хиро: заголовок и первая сфера шахматки (JS стартует с машин)
    idx = max(0, next((i for i, w in enumerate(j['words']) if w[1] == 'cars'), 0))
    word, key = j['words'][idx]
    s = sub_one(r'(<span class="h1-row" id="h1Pre")>[^<]*',
                lambda m: m.group(1) + (' hidden>' if not j['h1']['pre'] else '>') + j['h1']['pre'], s)
    s = sub_one(r'(<span class="h1-row" id="h1Post">)[^<]*', lambda m: m.group(1) + j['h1']['post'], s)
    s = sub_one(r'(<span class="sr" id="h1Sr">)[^<]*', lambda m: m.group(1) + html.escape(j['h1']['sr']), s)
    s = sub_one(r'(<span class="tw" id="tw">)[^<]*', lambda m: m.group(1) + html.escape(word), s)
    s = sub_one(r'(<span class="dom-chip" id="domChip"><svg><use href="#i-car"/></svg><span>)[^<]*',
                lambda m: m.group(1) + html.escape(j['labels'][key]), s)
    s = sub_one(r'(<b id="nTitle">)[^<]*', lambda m: m.group(1) + html.escape(j['notes'][key]), s)
    pay = int(re.search(r'const PAY = \{[^}]*\bcars: (\d+)', src).group(1))
    s = sub_one(r'(<b id="payAmt">)[^<]*', lambda m: m.group(1) + '+' + money(lang, pay), s)
    units = j.get('units', {}).get(key) or re.search(r"cars: (\[[^\]]+\])", src).group(1)
    if isinstance(units, str):
        units = json.loads(units.replace("'", '"'))
    s = sub_one(r'(<p id="nSub">)[^<]*', lambda m: m.group(1) + html.escape(f"{j['guests'][key][3]} · {units[1]}"), s)

    s = sub_one(r'<span id="langCode">[^<]*', f'<span id="langCode">{t["lang.code"]}', s)
    s = sub_one(r'<html lang="ru" dir="ltr">', f'<html lang="{lang}" dir="{"rtl" if lang in RTL else "ltr"}">', s)
    s = sub_one(r'<title>[^<]*</title>', f'<title>{attr(t["meta.title"])}</title>', s)
    s = sub_one(r'<meta name="description" content="[^"]*">',
                f'<meta name="description" content="{attr(t["meta.desc"])}">', s)

    if lang != 'ru':
        s = re.sub(r'\n\s*<li data-ru-only>.*?</li>', '', s)
        s = sub_one(r'<a class="link" id="supportLink" href="[^"]*" target="_blank" rel="noopener">',
                    f'<a class="link" id="supportLink" href="mailto:{EMAIL}">', s)
        s = sub_one(r'(<a class="store" id="appStoreLink" href=")[^"]*', lambda m: m.group(1) + APP_STORE, s)

    def lang_links(cls):
        out = []
        for l in LANGS:
            out.append(
                f'<a class="{cls}" href="{page_path(l)}" hreflang="{l}" lang="{l}" dir="{"rtl" if l in RTL else "ltr"}" '
                f'data-lang="{l}" role="menuitemradio" aria-checked="{str(l == lang).lower()}">'
                f'<span>{all_t[l]["lang.native"]}</span><svg class="ico"><use href="#i-check"/></svg></a>')
        return ''.join(out)
    s = s.replace('%%LANG_ITEMS%%', lang_links('lang-item')).replace('%%LANG_CHIPS%%', lang_links('lang-chip'))

    s = s.replace('%%FONTS%%', font_tags(lang)).replace('%%ANALYTICS%%', analytics(lang))
    s = s.replace('%%HEAD%%', head(lang, all_t))
    s = s.replace('%%I18N%%', json.dumps(t, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    return s


# Общее для всех страниц: шрифты, аналитика, баннер App Store

SMART_BANNER = '<meta name="apple-itunes-app" content="app-id=1631552064">'


def font_tags(lang: str) -> str:
    """@font-face прямо в странице (браузер скачает только нужные наборы символов) и прелоад основных файлов."""
    manifest = json.loads((HERE / 'assets' / 'fonts' / 'fonts.json').read_text())
    keys = FONTS + ([EXTRA_FONTS[lang]] if lang in EXTRA_FONTS else [])
    faces = '\n'.join(f['css'] for k in keys for f in manifest[k])
    subset = 'cyrillic' if lang == 'ru' else 'latin'
    preload = [f'golos-{subset}-400.woff2', f'onest-{subset}-700.woff2'] if lang not in EXTRA_FONTS else []
    links = ''.join(f'<link rel="preload" href="/fonts/{f}" as="font" type="font/woff2" crossorigin>\n' for f in preload)
    return f'{links}<style>\n{faces}\n</style>'


def analytics(lang: str) -> str:
    out = []
    if CF_ANALYTICS_TOKEN:
        out.append('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                   f'data-cf-beacon=\'{{"token": "{CF_ANALYTICS_TOKEN}"}}\'></script>')
    if YANDEX_METRIKA_ID and lang == 'ru':
        out.append(f'''<script>
(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})
(window,document,'script','https://mc.yandex.ru/metrika/tag.js','ym');
ym({YANDEX_METRIKA_ID},'init',{{clickmap:true,trackLinks:true,accurateTrackBounce:true}});
</script>''')
    return '\n'.join(out)


def shot_url(lang: str, name: str) -> str:
    return f'{SITE}/shots/{lang}/{name}.webp'


def shots_for(lang: str, wanted: list = None) -> list:
    """Скриншоты, которые есть для языка (tools/shots.py пропускает подписи с длинным тире), в порядке wanted."""
    have = [n for n in SHOTS if (HERE / 'assets' / 'shots' / lang / f'{n}.webp').exists()]
    order = [n for n in (wanted or []) if n in have]
    return order + [n for n in have if n not in order]


# Ключевые функции для разметки schema.org (featureList), из словаря тарифов
FEATURE_KEYS = ['price.f2', 'price.f4', 'price.b3', 'price.b4', 'price.p2', 'price.p3', 'price.p4', 'price.p5',
                'price.z2', 'price.z3', 'price.z4', 'price.f5']


# <head>: canonical, hreflang, Open Graph, разметка schema.org, выбор языка

LANG_SCRIPT = '''<script>
(function () {
  /* Корень сайта открывает версию на языке браузера; выбор пользователя запоминается. Боты остаются на месте */
  var langs = %s, cis = %s, here = document.documentElement.lang, target = null;
  var m = location.hash.match(/^#lang-([a-z]{2})$/);
  if (m && langs.indexOf(m[1]) >= 0) {
    target = m[1];
    try { localStorage.setItem('rp-lang', target); } catch (e) { /* storage unavailable */ }
  } else if (here === '%s' && !/bot|crawl|spider|slurp|lighthouse|headless|preview/i.test(navigator.userAgent)) {
    try { target = localStorage.getItem('rp-lang'); } catch (e) { /* storage unavailable */ }
    if (langs.indexOf(target) < 0) {
      target = '%s';
      var list = navigator.languages || [navigator.language || ''];
      for (var i = 0; i < list.length; i++) {
        var code = (list[i] || '').slice(0, 2).toLowerCase();
        if (langs.indexOf(code) >= 0) { target = code; break; }
        if (cis.indexOf(code) >= 0) { target = 'ru'; break; }
      }
    }
  }
  if (target && target !== here) location.replace(target === '%s' ? '/' : '/' + target + '/');
})();
</script>'''


def org_ld(lang: str) -> dict:
    return {
        '@type': 'Organization', '@id': f'{SITE}/#org', 'name': 'DGL Factor', 'url': f'{SITE}/',
        'logo': f'{SITE}/icon-512.png', 'email': EMAIL,
        'sameAs': [APP_STORE, GOOGLE_PLAY] + ([TG_CHANNEL] if lang == 'ru' else []),
    }


def json_ld(lang: str, t: dict) -> str:
    cur = 'RUB' if lang == 'ru' else 'USD'
    table = PRICES['rub' if lang == 'ru' else 'usd']
    org = org_ld(lang)
    app = {
        '@type': 'SoftwareApplication', '@id': f'{page_url(lang)}#app', 'name': t['app.name'],
        'description': plain(lang, t['meta.desc']), 'url': page_url(lang), 'inLanguage': lang,
        'image': f'{SITE}/og/{lang}.png', 'screenshot': [shot_url(lang, n) for n in shots_for(lang)],
        'featureList': [plain(lang, t[k]) for k in FEATURE_KEYS], 'applicationCategory': 'BusinessApplication',
        'operatingSystem': 'iOS, Android, Web', 'downloadUrl': [APP_STORE_RU if lang == 'ru' else APP_STORE, GOOGLE_PLAY],
        'offers': {
            '@type': 'AggregateOffer', 'priceCurrency': cur, 'lowPrice': 0,
            'highPrice': max(v[0] for v in table.values()), 'offerCount': len(table),
        },
        'aggregateRating': {'@type': 'AggregateRating', 'ratingValue': RATING, 'ratingCount': RATING_COUNT, 'bestRating': 5},
        'publisher': {'@id': f'{SITE}/#org'},
    }
    site = {
        '@type': 'WebSite', '@id': f'{SITE}/#website', 'url': f'{SITE}/', 'name': t['app.name'],
        'inLanguage': lang, 'publisher': {'@id': f'{SITE}/#org'},
    }
    faq = {
        '@type': 'FAQPage', '@id': f'{page_url(lang)}#faq', 'inLanguage': lang,
        'mainEntity': [
            {'@type': 'Question', 'name': plain(lang, t[f'faq.q{i}']),
             'acceptedAnswer': {'@type': 'Answer', 'text': plain(lang, t[f'faq.a{i}'])}}
            for i in range(1, 20) if f'faq.q{i}' in t
        ],
    }
    data = {'@context': 'https://schema.org', '@graph': [org, site, app, faq]}
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def head(lang: str, all_t: dict) -> str:
    t = all_t[lang]
    title, desc = attr(t['meta.title']), attr(t['meta.desc'])
    lines = [f'<link rel="canonical" href="{page_url(lang)}">']
    lines += [f'<link rel="alternate" hreflang="{l}" href="{page_url(l)}">' for l in LANGS]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{page_url(X_DEFAULT)}">')
    lines += [
        '<meta name="theme-color" content="#F7F8FC">',
        SMART_BANNER,
        '<link rel="icon" type="image/png" href="/logo.png">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{attr(t["app.name"])}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        f'<meta property="og:url" content="{page_url(lang)}">',
        f'<meta property="og:image" content="{SITE}/og/{lang}.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{title}">',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}">',
    ]
    lines += [f'<meta property="og:locale:alternate" content="{OG_LOCALE[l]}">' for l in LANGS if l != lang]
    lines += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{desc}">',
        f'<meta name="twitter:image" content="{SITE}/og/{lang}.png">',
        f'<script type="application/ld+json">{json_ld(lang, t)}</script>',
        LANG_SCRIPT % (json.dumps(LANGS), json.dumps(CIS), ROOT_LANG, X_DEFAULT, ROOT_LANG),
    ]
    return '\n'.join(lines)


# Страницы сфер и блог на общем шаблоне templates/layout.html

def sphere_path(lang: str, key: str) -> str:
    return f'{page_path(lang)}{SPHERES[key]["slug"]}/'


def blog_path(lang: str) -> str:
    return f'{page_path(lang)}blog/'


def load_spheres() -> dict:
    ref = json.loads((HERE / 'spheres' / 'en.json').read_text())
    out, errs = {}, []
    for lang in LANGS:
        data = json.loads((HERE / 'spheres' / f'{lang}.json').read_text())
        for key in SPHERES:
            sp = data.get(key)
            if not sp:
                errs.append(f'spheres/{lang}.json: нет сферы {key}')
                continue
            errs += [f'spheres/{lang}.json: в {key} нет {k}' for k in ref[key] if k not in sp]
            if len(sp.get('features', [])) != 6 or len(sp.get('faq', [])) != 4:
                errs.append(f'spheres/{lang}.json: в {key} нужно 6 features и 4 faq')
        out[lang] = data
    if errs:
        raise SystemExit('\n'.join(errs))
    return out


def load_blog() -> dict:
    """Посты из blog/<lang>/<slug>.md (их пишет Sveltia CMS). Перевод поста лежит под тем же slug в папке другого языка."""
    posts, errs = {}, []
    for lang in LANGS:
        for f in sorted((HERE / 'blog' / lang).glob('*.md')) if (HERE / 'blog' / lang).exists() else []:
            meta, body = mdlite.front_matter(f.read_text())
            if meta.get('draft') == 'true':
                continue
            errs += [f'blog/{lang}/{f.name}: нет поля {k}' for k in ('title', 'description', 'date') if not meta.get(k)]
            date = meta.get('date', '')[:10]
            posts.setdefault(lang, []).append({
                'slug': f.stem, 'title': meta.get('title', ''), 'description': meta.get('description', ''),
                'date': date, 'updated': max(date, meta.get('updated', '')[:10]),
                'cover': meta.get('cover', ''), 'html': mdlite.to_html(body),
            })
    if errs:
        raise SystemExit('\n'.join(errs))
    for items in posts.values():
        items.sort(key=lambda x: x['date'], reverse=True)
    return posts


def image_size(src: str):
    """(ширина, высота) картинки блога по её адресу на сайте, из заголовка файла WebP, PNG или JPEG."""
    if not src.startswith('/media/blog/'):
        return None
    f = HERE / 'assets' / 'blog' / src[len('/media/blog/'):]
    if not f.is_file():
        return None
    b = f.read_bytes()
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        if b[12:16] == b'VP8 ':
            return int.from_bytes(b[26:28], 'little') & 0x3fff, int.from_bytes(b[28:30], 'little') & 0x3fff
        if b[12:16] == b'VP8L':
            v = int.from_bytes(b[21:25], 'little')
            return (v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1
        if b[12:16] == b'VP8X':
            return int.from_bytes(b[24:27], 'little') + 1, int.from_bytes(b[27:30], 'little') + 1
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big')
    if b[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(b):
            marker, length = b[i + 1], int.from_bytes(b[i + 2:i + 4], 'big')
            if marker in (0xC0, 0xC1, 0xC2):
                return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
            i += 2 + length
    return None


mdlite.image_size = image_size


def fmt_date(lang: str, iso: str) -> str:
    y, m, d = (int(x) for x in iso[:10].split('-'))
    if lang == 'en':
        return f'{EN_MONTHS[m - 1]} {d}, {y}'
    sep = '.' if lang in ('ru', 'de', 'tr') else '/'
    return f'{d:02d}{sep}{m:02d}{sep}{y}'


def stores(lang: str, t: dict, anchor: bool = False) -> str:
    ios = APP_STORE_RU if lang == 'ru' else APP_STORE
    anchor_id = ' id="download"' if anchor else ''
    return (f'<div class="stores"{anchor_id}>'
            f'<a class="store" href="{ios}" target="_blank" rel="noopener"><svg><use href="#i-apple"/></svg>'
            f'<span><small>{t["cta.as"]}</small><b>App Store</b></span></a>'
            f'<a class="store" href="{GOOGLE_PLAY}" target="_blank" rel="noopener"><svg><use href="#i-play"/></svg>'
            f'<span><small>{t["cta.gp"]}</small><b>Google Play</b></span></a></div>')


def cta_block(lang: str, t: dict) -> str:
    return (f'<div class="wrap"><section class="cta"><h2>{t["cta.title"]}</h2><p>{t["cta.sub"]}</p>'
            f'{stores(lang, t)}</section></div>')


def faq_block(items: list, title: str) -> str:
    rows = ''.join(f'<details><summary>{q}<svg class="ico"><use href="#i-plus"/></svg></summary><div class="ans">{a}</div></details>'
                   for q, a in items)
    return f'<section class="sec"><div class="wrap"><h2>{title}</h2><div class="faq">{rows}</div></div></section>'


def faq_ld(lang: str, items: list, url: str) -> dict:
    return {'@type': 'FAQPage', '@id': f'{url}#faq', 'inLanguage': lang, 'mainEntity': [
        {'@type': 'Question', 'name': plain(lang, q), 'acceptedAnswer': {'@type': 'Answer', 'text': plain(lang, a)}}
        for q, a in items]}


def crumbs_ld(items: list) -> dict:
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i, 'name': plain('en', name), 'item': f'{SITE}{path}'}
        for i, (name, path) in enumerate(items, 1)]}


def crumbs(items: list) -> str:
    sep = '<li aria-hidden="true"><svg class="ico flip"><use href="#i-chev"/></svg></li>'
    parts = [f'<li><a href="{path}">{name}</a></li>' for name, path in items[:-1]]
    parts.append(f'<li aria-current="page">{items[-1][0]}</li>')
    return f'<ol class="crumbs">{sep.join(parts)}</ol>'


def footer(lang: str, t: dict, blog_langs: set) -> str:
    home = page_path(lang)
    ext = 'target="_blank" rel="noopener"'
    spheres = ''.join(f'<li><a href="{sphere_path(lang, k)}">{t["sph." + k]}</a></li>' for k in SPHERES)
    blog = f'<li><a href="{blog_path(lang)}">{t["blog.title"]}</a></li>' if lang in blog_langs else ''
    tg = (f'<li><a href="{TG_CHANNEL}" {ext}>{t["foot.tg"]}</a></li><li><a href="{TG_BOT}" {ext}>{t["foot.bot"]}</a></li>'
          if lang == 'ru' else '')
    return f'''<footer><div class="wrap"><div class="f-grid">
<div class="f-about"><a class="brand" href="{home}"><img src="/logo.png" alt="" width="40" height="40"><span>{t["app.name"]}</span></a><p>{t["foot.about"]}</p></div>
<div><h6>{t["nav.who"]}</h6><ul>{spheres}</ul></div>
<div><h6>{t["foot.product"]}</h6><ul><li><a href="{home}#features">{t["nav.features"]}</a></li><li><a href="{home}#pricing">{t["nav.pricing"]}</a></li>{blog}<li><a href="{WEB_APP}" {ext}>{t["nav.web"]}</a></li><li><a href="{API_DOCS}" {ext}>API</a></li></ul></div>
<div><h6>{t["foot.contact"]}</h6><ul>{tg}<li><a href="mailto:{EMAIL}">{EMAIL}</a></li></ul><h6 class="f-docs">{t["foot.docs"]}</h6><ul><li><a href="/terms">{t["foot.terms"]}</a></li><li><a href="/privacy">{t["foot.privacy"]}</a></li></ul></div>
</div><div class="f-bottom">© 2026 DGL Factor</div></div></footer>'''


def layout(lang: str, all_t: dict, ctx: dict, *, title: str, desc: str, path: str, alternates: dict,
           main: str, ld: list, og_type: str = 'website', image: str = '', noindex: bool = False,
           meta: tuple = ()) -> str:
    t = all_t[lang]
    url = f'{SITE}{path}'
    image = image or f'{SITE}/og/{lang}.png'
    head = ['<meta name="robots" content="noindex">' if noindex else f'<link rel="canonical" href="{url}">']
    if len(alternates) > 1:
        head += [f'<link rel="alternate" hreflang="{l}" href="{SITE}{p}">' for l, p in alternates.items()]
        if X_DEFAULT in alternates:
            head.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}{alternates[X_DEFAULT]}">')
    head += [
        '<meta name="theme-color" content="#F7F8FC">', SMART_BANNER,
        '<link rel="icon" type="image/png" href="/logo.png">', '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        f'<meta property="og:type" content="{og_type}">', f'<meta property="og:site_name" content="{attr(t["app.name"])}">',
        f'<meta property="og:title" content="{attr(title)}">', f'<meta property="og:description" content="{attr(desc)}">',
        f'<meta property="og:url" content="{url}">', f'<meta property="og:image" content="{image}">',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}">', *meta, '<meta name="twitter:card" content="summary_large_image">',
        '<script type="application/ld+json">'
        + json.dumps({'@context': 'https://schema.org', '@graph': ld}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        + '</script>',
    ]
    links = ''.join(
        f'<a href="{alternates.get(l, page_path(l))}" hreflang="{l}" lang="{l}" dir="{"rtl" if l in RTL else "ltr"}" data-lang="{l}"'
        f' aria-current="{str(l == lang).lower()}"><span>{all_t[l]["lang.native"]}</span><svg class="ico"><use href="#i-check"/></svg></a>'
        for l in LANGS)
    values = {
        'LANG': lang, 'DIR': 'rtl' if lang in RTL else 'ltr', 'TITLE': attr(title), 'DESC': attr(desc),
        'HEAD': '\n'.join(head), 'FONTS': font_tags(lang), 'CSS': ctx['css'], 'SPRITE': ctx['sprite'],
        'HOME': page_path(lang), 'APP': t['app.name'], 'LANG_LABEL': attr(t['nav.lang']), 'LANG_CODE': t['lang.code'],
        'LANG_LINKS': links, 'DOWNLOAD': t['cta.download'], 'MAIN': main, 'FOOTER': footer(lang, t, ctx['blog_langs']),
        'APP_STORE': APP_STORE, 'GOOGLE_PLAY': GOOGLE_PLAY, 'ANALYTICS': analytics(lang),
    }
    return re.sub(r'%%([A-Z_]+)%%', lambda m: values[m.group(1)], ctx['layout'])


def sphere_pages(all_t: dict, spheres: dict, ctx: dict) -> dict:
    out = {}
    for lang in LANGS:
        t = all_t[lang]
        for key, conf in SPHERES.items():
            sp, path = spheres[lang][key], sphere_path(lang, key)
            url = f'{SITE}{path}'
            w, h = SHOT_SIZE
            alt = attr(f'{t["app.name"]}: {html.unescape(sp["h1"])}')
            picked = shots_for(lang, conf['shots'])[:4]
            shots = [f'<img src="/shots/{lang}/{n}.webp" width="{w}" height="{h}" alt="{alt}" loading="lazy">' for n in picked[1:]]
            cards = ''.join(f'<article class="card"><h3><svg class="ico"><use href="#i-check"/></svg>{f["t"]}</h3><p>{f["d"]}</p></article>'
                            for f in sp['features'])
            others = ''.join(f'<a href="{sphere_path(lang, k)}"><svg><use href="#i-{c["icon"]}"/></svg>{t["sph." + k]}</a>'
                             for k, c in SPHERES.items() if k != key)
            trail = [(t['app.name'], page_path(lang)), (t['sph.' + key], path)]
            main = f'''<section class="hero"><div class="wrap hero-grid"><div>
{crumbs(trail)}
<h1>{sp["h1"]}</h1><p class="lead">{sp["lead"]}</p>
{stores(lang, t, anchor=True)}
<a class="web" href="{WEB_APP}" target="_blank" rel="noopener">{t["cta.web"]}<svg class="ico flip"><use href="#i-chev"/></svg></a>
<p class="rating"><span class="stars" aria-hidden="true">{'<svg><use href="#i-star"/></svg>' * 5}</span><b>{fmt(lang, RATING, 1)}</b><span>{t["hero.rateT"]}</span></p>
</div><img class="phone" src="/shots/{lang}/{picked[0]}.webp" width="{w}" height="{h}" alt="{alt}" fetchpriority="high"></div></section>
<section class="sec"><div class="wrap"><h2>{sp["features_title"]}</h2><div class="cards">{cards}</div></div></section>
<section class="sec" style="padding-top:0"><div class="wrap"><div class="gallery">{''.join(shots)}</div></div></section>
{faq_block([(q["q"], q["a"]) for q in sp["faq"]], t["faq.title"])}
<section class="sec" style="padding-top:0"><div class="wrap"><h2>{t["sph.title"]}</h2><nav class="others">{others}</nav></div></section>
{cta_block(lang, t)}'''
            ld = [
                {'@type': 'WebPage', '@id': url, 'url': url, 'name': plain(lang, sp['title']), 'description': plain(lang, sp['desc']),
                 'inLanguage': lang, 'isPartOf': {'@id': f'{SITE}/#website'}, 'about': {'@id': f'{page_url(lang)}#app'},
                 'primaryImageOfPage': shot_url(lang, picked[0])},
                crumbs_ld([(plain(lang, n), p) for n, p in trail]),
                faq_ld(lang, [(q['q'], q['a']) for q in sp['faq']], url),
            ]
            alternates = {l: sphere_path(l, key) for l in LANGS}
            out[path.strip('/') + '/index.html'] = layout(
                lang, all_t, ctx, title=sp['title'], desc=sp['desc'], path=path, alternates=alternates, main=main, ld=ld)
    return out


def blog_pages(all_t: dict, posts: dict, ctx: dict) -> dict:
    out = {}
    for lang, items in posts.items():
        t = all_t[lang]
        index = blog_path(lang)
        cards = ''.join(
            f'<a class="post-card" href="{index}{p["slug"]}/">'
            + (f'<img src="{p["cover"]}" alt="" loading="lazy" width="1200" height="675">' if p['cover'] else '')
            + f'<div><h2>{html.escape(p["title"])}</h2><p>{html.escape(p["description"])}</p>'
              f'<time datetime="{p["date"]}">{fmt_date(lang, p["date"])}</time></div></a>'
            for p in items)
        trail = [(t['app.name'], page_path(lang)), (t['blog.title'], index)]
        main = (f'<section class="hero"><div class="wrap">{crumbs(trail)}<h1>{t["blog.title"]}</h1><p class="lead">{t["blog.sub"]}</p></div></section>'
                f'<section class="sec" style="padding-top:8px"><div class="wrap"><div class="posts">{cards}</div></div></section>'
                + cta_block(lang, t))
        ld = [{'@type': 'Blog', '@id': f'{SITE}{index}', 'url': f'{SITE}{index}', 'name': plain(lang, t['blog.title']),
               'description': plain(lang, t['blog.sub']), 'inLanguage': lang, 'publisher': {'@id': f'{SITE}/#org'},
               'blogPost': [{'@type': 'BlogPosting', 'headline': p['title'], 'url': f'{SITE}{index}{p["slug"]}/',
                             'datePublished': p['date'], 'dateModified': p['updated']} for p in items]},
              org_ld(lang), crumbs_ld([(plain(lang, n), pth) for n, pth in trail])]
        alternates = {l: blog_path(l) for l in posts}
        out[index.strip('/') + '/index.html'] = layout(
            lang, all_t, ctx, title=f'{html.unescape(t["blog.title"])} | {t["app.name"]}', desc=plain(lang, t['blog.sub']),
            path=index, alternates=alternates, main=main, ld=ld)
        for p in items:
            path = f'{index}{p["slug"]}/'
            url = f'{SITE}{path}'
            w, h = image_size(p['cover']) or (1200, 675)
            cover = (f'<img class="cover" src="{p["cover"]}" alt="{attr(p["title"])}" width="{w}" height="{h}" fetchpriority="high">'
                     if p['cover'] else '')
            main = (f'<section class="sec" style="padding-top:28px"><div class="wrap narrow">'
                    f'<a class="back" href="{index}"><svg class="ico" style="transform:scaleX(-1)"><use href="#i-chev"/></svg>{t["blog.back"]}</a>'
                    f'<article class="article"><h1>{html.escape(p["title"])}</h1>'
                    f'<time class="post-meta" datetime="{p["date"]}">{fmt_date(lang, p["date"])}</time>{cover}'
                    f'<div class="prose">{p["html"]}</div></article></div></section>' + cta_block(lang, t))
            image = f'{SITE}{p["cover"]}' if p['cover'] else f'{SITE}/og/{lang}.png'
            ld = [{'@type': 'BlogPosting', '@id': url, 'url': url, 'mainEntityOfPage': url, 'headline': p['title'],
                   'description': p['description'], 'datePublished': p['date'], 'dateModified': p['updated'],
                   'inLanguage': lang, 'image': image,
                   'author': {'@id': f'{SITE}/#org'}, 'publisher': {'@id': f'{SITE}/#org'}, 'isPartOf': {'@id': f'{SITE}{index}'}},
                  org_ld(lang),
                  crumbs_ld([(plain(lang, t['app.name']), page_path(lang)), (plain(lang, t['blog.title']), index), (p['title'], path)])]
            alternates = {l: f'{blog_path(l)}{p["slug"]}/' for l, li in posts.items() if any(x['slug'] == p['slug'] for x in li)}
            # Название приложения в title, только пока он влезает в выдачу поисковика (около 60 знаков)
            title = f'{p["title"]} | {t["app.name"]}'
            if len(title) > 60:
                title = p['title']
            meta = (f'<meta property="article:published_time" content="{p["date"]}">',
                    f'<meta property="article:modified_time" content="{p["updated"]}">')
            out[path.strip('/') + '/index.html'] = layout(
                lang, all_t, ctx, title=title, desc=p['description'], path=path,
                alternates=alternates, main=main, ld=ld, og_type='article', image=image, meta=meta)
    return out


def not_found_pages(all_t: dict, ctx: dict) -> dict:
    """404.html в папке каждого языка: хостинг отдаёт ближайшую к запрошенному адресу."""
    out = {}
    for lang in LANGS:
        t = all_t[lang]
        home = page_path(lang)
        spheres = ''.join(f'<a href="{sphere_path(lang, k)}"><svg><use href="#i-{c["icon"]}"/></svg>{t["sph." + k]}</a>'
                          for k, c in SPHERES.items())
        main = (f'<section class="hero"><div class="wrap"><h1>{t["nf.title"]}</h1><p class="lead">{t["nf.text"]}</p>'
                f'<a class="btn btn-primary nf-home" href="{home}">{t["nf.home"]}</a></div></section>'
                f'<section class="sec" style="padding-top:0"><div class="wrap"><h2>{t["sph.title"]}</h2><nav class="others">{spheres}</nav></div></section>')
        out[home.strip('/') + ('/' if lang != ROOT_LANG else '') + '404.html'] = layout(
            lang, all_t, ctx, title=f'{t["nf.title"]} | {t["app.name"]}', desc=plain(lang, t['nf.text']), path=home,
            alternates={}, main=main, ld=[], noindex=True)
    return out


# Файлы для поисковиков

def legal_pages() -> dict:
    shell = (HERE / 'legal' / 'page.html').read_text()
    out = {}
    for name, desc in LEGAL.items():
        content = (HERE / 'legal' / f'{name}.html').read_text()
        title = re.search(r'<h1>(.*?)</h1>', content).group(1)
        page = (shell.replace('%%TITLE%%', title).replace('%%DESC%%', attr(desc))
                .replace('%%URL%%', f'{SITE}/{name}').replace('%%OG%%', f'{SITE}/og/{ROOT_LANG}.png')
                .replace('%%CONTENT%%', content.strip())
                .replace('%%FONTS%%', font_tags('en')).replace('%%ANALYTICS%%', analytics('en')))
        out[f'{name}.html'] = page
    return out


def sitemap(entries: list) -> str:
    """entries: (путь, {язык: путь перевода}, lastmod или '')."""
    urls = ''
    for path, alts, lastmod in entries:
        links = ''
        if len(alts) > 1:
            links = ''.join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{p}"/>' for l, p in alts.items())
            if X_DEFAULT in alts:
                links += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{alts[X_DEFAULT]}"/>'
        lm = f'\n    <lastmod>{lastmod}</lastmod>' if lastmod else ''
        urls += f'\n  <url>\n    <loc>{SITE}{path}</loc>{lm}{links}\n  </url>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            f'{urls}\n</urlset>\n')


def robots() -> str:
    return ('# Поисковики и AI-поиск (OAI-SearchBot, Claude-SearchBot, PerplexityBot и другие) допущены ко всему сайту\n'
            'User-agent: *\nAllow: /\nDisallow: /admin/\n\n'
            f'Sitemap: {SITE}/sitemap.xml\n')


def llms_txt(all_t: dict) -> str:
    t, lang = all_t['en'], 'en'
    p = lambda k: plain(lang, t[k])
    usd = PRICES['usd']
    plans = []
    for plan, feats in (('free', 'f'), ('basic', 'b'), ('premium', 'p'), ('business', 'z')):
        m, y = usd[plan]
        price = 'free forever' if not m else f'{money(lang, m, raw=True, cents=True)}/month or {money(lang, y, raw=True, cents=True)}/year'
        items = ', '.join(p(f'price.{feats}{i}') for i in range(1, 6))
        plans.append(f'- {p("price." + plan)} ({price}): {p("price." + plan + "D")}. {items}.')
    faq = '\n\n'.join(f'### {p(f"faq.q{i}")}\n\n{p(f"faq.a{i}")}' for i in range(1, 20) if f'faq.q{i}' in t)
    langs = '\n'.join(f'- [{all_t[l]["lang.native"]}]({page_url(l)})' for l in LANGS)
    return f'''# Rental Planner

> {p("meta.desc")}

{p("foot.about")} Works on iPhone, iPad, Android and in the browser.

- App Store rating {RATING} from {RATING_COUNT}+ ratings
- 23K+ hosts, 760K+ bookings, 187 countries
- Booking site sync through iCal: Airbnb, Booking.com, Agoda
- Developer: DGL Factor, {EMAIL}

## Plans (USD, App Store USA)

{chr(10).join(plans)}

## Links

- [Website]({page_url("en")})
- [App Store]({APP_STORE})
- [Google Play]({GOOGLE_PLAY})
- [Web app]({WEB_APP})
- [API docs](https://rp-api.dglfactor.tech/docs/rental-planner-api)

## Use cases

{chr(10).join(f'- [{plain(lang, all_t["en"]["sph." + k])}]({SITE}{sphere_path("en", k)})' for k in SPHERES)}

## Languages

{langs}

## FAQ

{faq}
'''


def redirects() -> str:
    from urllib.parse import quote
    lines = ['# Старые адреса сайта на Wix (формат Cloudflare Workers, Pages и Netlify)']
    for src, dst in REDIRECTS:
        lines.append(f'{quote(src, safe="/*")}  {dst}  301')
    return '\n'.join(lines) + '\n'


def headers() -> str:
    # Шрифты, скриншоты и картинки меняются редко: браузер держит их месяц, страницы всегда проверяет заново
    cache = ''.join(f'/{d}/*\n  Cache-Control: public, max-age=2592000\n' for d in ('fonts', 'shots', 'media', 'og'))
    return ('# Технический адрес Cloudflare *.workers.dev не должен попадать в поиск, сайт живёт на своём домене\n'
            'https://:worker.:account.workers.dev/*\n  X-Robots-Tag: noindex\n' + cache)


def main(require_og: bool = True) -> None:
    src = (HERE / 'src.html').read_text()
    symbols = '\n'.join(symbol(n, f) for n, f in ICONS.items())
    src = src.replace('%%ICON_SYMBOLS%%', symbols).replace('%%SQUIGGLE%%', squiggle())
    src = src.replace('%%WEB_APP%%', WEB_APP).replace('%%WEB_HOST%%', WEB_APP.split('//')[1])
    src = src.replace('%%PRICES%%', json.dumps(PRICES)).replace('%%RUB_PER_USD%%', str(RUB_PER_USD))
    all_t = load_locales(src)
    spheres = load_spheres()
    posts = load_blog()
    blog_langs = set(posts)
    ctx = {
        'layout': (HERE / 'templates' / 'layout.html').read_text(),
        'css': (HERE / 'templates' / 'pages.css').read_text().strip(),
        'sprite': re.search(r'<svg width="0" height="0".*?</svg>', src, re.S).group(0),
        'blog_langs': blog_langs,
    }

    files = {}
    for lang in LANGS:
        files[page_file(lang)] = prerender(src, lang, all_t, blog_langs)
    files.update(sphere_pages(all_t, spheres, ctx))
    files.update(blog_pages(all_t, posts, ctx))
    files.update(not_found_pages(all_t, ctx))
    files.update(legal_pages())
    files['admin/index.html'] = (HERE / 'admin' / 'index.html').read_text()
    files['admin/config.yml'] = (HERE / 'admin' / 'config.yml').read_text()

    def mtime(*paths):
        return datetime.date.fromtimestamp(max(f.stat().st_mtime for f in paths)).isoformat()
    i18n_files = list((HERE / 'i18n').glob('*.json'))
    entries = [(page_path(l), {x: page_path(x) for x in LANGS}, mtime(HERE / 'src.html', *i18n_files)) for l in LANGS]
    sphere_mtime = mtime(*(HERE / 'spheres').glob('*.json'), *i18n_files)
    entries += [(sphere_path(l, k), {x: sphere_path(x, k) for x in LANGS}, sphere_mtime) for k in SPHERES for l in LANGS]
    for lang, items in posts.items():
        entries.append((blog_path(lang), {x: blog_path(x) for x in posts}, max(p['updated'] for p in items)))
        for p in items:
            alts = {x: f'{blog_path(x)}{p["slug"]}/' for x, li in posts.items() if any(y['slug'] == p['slug'] for y in li)}
            entries.append((f'{blog_path(lang)}{p["slug"]}/', alts, p['updated']))
    entries += [(f'/{name}', {}, '') for name in LEGAL]
    files['sitemap.xml'] = sitemap(entries)
    files['robots.txt'] = robots()
    files[f'{INDEXNOW_KEY}.txt'] = INDEXNOW_KEY
    files['llms.txt'] = llms_txt(all_t)
    files['_redirects'] = redirects()
    files['_headers'] = headers()

    errs = []
    for name, text in files.items():
        if '%%' in text and name.endswith('.html'):
            errs.append(f'{name}: остался плейсхолдер {re.search(r"%%[A-Z_]+%%", text).group(0)}')
        for bad in ('\u2014', '\u2013'):
            if bad in text:
                errs.append(f'{name}: запрещённое тире {bad!r}')
    og = HERE / 'assets' / 'og'
    if require_og:
        errs += [f'нет картинки для соцсетей assets/og/{l}.png (python3 tools/og.py)' for l in LANGS if not (og / f'{l}.png').exists()]
    if errs:
        raise SystemExit('\n'.join(errs))

    if DIST.exists():
        shutil.rmtree(DIST)
    for name, text in files.items():
        out = DIST / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    shutil.copytree(HERE / 'assets' / 'fonts', DIST / 'fonts', ignore=shutil.ignore_patterns('*.json'))
    shutil.copytree(HERE / 'assets' / 'shots', DIST / 'shots')
    if (HERE / 'assets' / 'blog').exists():
        shutil.copytree(HERE / 'assets' / 'blog', DIST / 'media' / 'blog')
    for f in ('logo.png', 'apple-touch-icon.png', 'icon-512.png'):
        shutil.copy(HERE / 'assets' / f, DIST / f)
    if og.exists():
        shutil.copytree(og, DIST / 'og')
    pages = sum(1 for n in files if n.endswith('.html'))
    print('ok', pages, 'pages;', ', '.join(f'{l} {len(files[page_file(l)].encode()) // 1024}K' for l in LANGS))


if __name__ == '__main__':
    main()
