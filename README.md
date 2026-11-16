# Rental Planner: сайт

Сайт приложения Rental Planner (Планировщик аренды) на 10 языках приложения: ru, en, de, es, fr, pt, tr, ar, he, th. Статичные страницы без фреймворков и зависимостей: лендинг, страницы сфер, блог с админкой и юридические страницы.

## Сборка

```sh
python3 build.py        # → dist/
python3 preview.py      # сборка + локальный сервер на http://localhost:8000
python3 tools/og.py     # переснять картинки для соцсетей (нужен Google Chrome)
python3 tools/shots.py  # обновить скриншоты из сторов (нужны realtor-manage-app рядом и cwebp)
python3 tools/fonts.py  # заново скачать шрифты (только при смене шрифтов)
python3 tools/indexnow.py  # после деплоя: сообщить Bing и Яндексу об обновлениях
```

`build.py` собирает в `dist/`:

- **лендинг** из `src.html`, отдельно на каждый язык: `index.html` (en) и `<lang>/index.html`. Тексты, цены и числа вшиваются в HTML при сборке, поэтому поисковики и AI-краулеры видят готовую страницу без JS;
- **страницы сфер** `<lang>/<slug>/` из `spheres/<lang>.json` (6 сфер × 10 языков);
- **блог** `<lang>/blog/` и `<lang>/blog/<slug>/` из `blog/<lang>/*.md`, только для языков, где есть посты;
- **юридические страницы** `terms.html` и `privacy.html` из `legal/`;
- **страницы 404** `404.html` (en) и `<lang>/404.html`: хостинг отдаёт ближайшую к запрошенному адресу, закрыты от индексации;
- **админку блога** `admin/` (Sveltia CMS);
- `sitemap.xml`, `robots.txt`, `llms.txt`, `_redirects`, `_headers`, ключ IndexNow, шрифты, скриншоты, иконки, `og/<lang>.png`.

На всех страницах: canonical, hreflang, Open Graph, разметка schema.org (приложение с рейтингом и функциями, FAQ, хлебные крошки, посты), баннер App Store для Safari на iPhone. Шрифты раздаются со своего домена, `@font-face` вшиты в страницу.

Сборка проверяет, что во всех языках есть все ключи и сферы, и падает на длинном тире в любом файле. Цены тарифов и курс для пересчёта живут в `build.py` (`PRICES`, `RUB_PER_USD`), JS страницы получает их оттуда же.

## Структура

| Путь | Что это |
|---|---|
| `src.html` | Разметка, стили и JS лендинга. Русский текст живёт прямо в разметке |
| `i18n/ru.json` | Русские данные: title, description, тексты блога и данные для JS (печатающийся заголовок, объекты и гости шахматки) |
| `i18n/<lang>.json` | Остальные языки: все ключи `data-i` / `data-ia` + блок `_js` |
| `spheres/<lang>.json` | Тексты страниц сфер: title, description, заголовок, 6 функций, 4 вопроса. Адреса, иконки и скриншоты сфер в `SPHERES` в `build.py` |
| `blog/<lang>/<slug>.md` | Посты блога (Markdown с шапкой title, description, date, updated, cover, draft). Перевод поста лежит под тем же slug в папке другого языка |
| `admin/` | Админка блога: `index.html` грузит Sveltia CMS, `config.yml` её настройки |
| `wrangler.jsonc` | Настройки Cloudflare Workers: раздавать `dist/` как статику, 404 и адреса без `.html` |
| `templates/` | Общий шаблон (`layout.html`) и стили (`pages.css`) страниц сфер и блога |
| `mdlite.py` | Markdown в HTML для постов, без зависимостей |
| `legal/` | Условия использования и политика конфиденциальности (только английский): `page.html` шаблон, `terms.html` и `privacy.html` тексты. Перенесены с Wix как есть |
| `assets/icons/` | Иконки сфер из приложения (`assets/svg` в realtor-manage-app) |
| `assets/logo.png` | Иконка приложения, 128px (favicon и логотип на странице) |
| `assets/apple-touch-icon.png`, `assets/icon-512.png` | Иконка приложения 180 и 512px (из AppIcon в realtor-manage-app) |
| `assets/og/` | Картинки для соцсетей 1200×630, снимаются `tools/og.py` с хиро каждой версии |
| `assets/shots/<lang>/` | Скриншоты из сторов в WebP (из `tool/aso/out/iphone/screenshots` в realtor-manage-app) |
| `assets/fonts/` | Шрифты woff2 и `fonts.json` (какой `@font-face` к какому файлу) |
| `assets/blog/` | Картинки постов, на сайте лежат в `/media/blog/` |
| `tools/` | Генераторы картинок, скриншотов, шрифтов и отправка IndexNow |
| `dist/` | Результат сборки, в git не попадает |

## Как добавить или поменять текст

1. В `src.html` у элемента атрибут `data-i="section.key"`, русский текст внутри него.
2. Тот же ключ добавить во все `i18n/<lang>.json`.
3. `python3 build.py` скажет, если где-то ключа не хватает.

Деньги в текстах пишутся токеном `{m:12000}` (сумма в рублях): в русской версии подставятся рубли, в остальных доллары.

Если поменялся хиро или его тексты, перезапусти `python3 tools/og.py`, чтобы обновились превью в соцсетях.

## Язык страницы

У каждого языка свой адрес: английский в корне (`/`), остальные в `/ru/`, `/de/` и так далее. Меню языков состоит из обычных ссылок между версиями.

Корень сам открывает версию на языке браузера (для языков СНГ русскую, для неизвестных остаётся английский), ручной выбор запоминается. Внутренние версии (`/ru/`, `/de/` и т.п.) никуда не перенаправляют. Боты остаются на той странице, которую запросили. Принудительно: `#lang-de` в адресе.

## Блог и админка

Посты пишутся в админке на `https://www.rentalplanner.io/admin/`. Sveltia CMS сохраняет их коммитом в репозиторий (`blog/<lang>/<slug>.md`, картинки в `assets/blog/`), хостинг пересобирает сайт. Язык по умолчанию русский, перевод включается в редакторе поста для любого из 10 языков. Раздел блога и ссылка на него в футере появляются в языке, как только там есть хотя бы один пост.

Чтобы админка заработала:

1. Репозиторий: [Diaglyonok/rental-planner-site](https://github.com/Diaglyonok/rental-planner-site), он указан в `admin/config.yml` (`backend.repo`).
2. Подключить хостинг к репозиторию, см. «Деплой».
3. Вход кнопкой «Sign In with GitHub» идёт через [Sveltia CMS Authenticator](https://github.com/sveltia/sveltia-cms-auth): Worker `sveltia-cms-auth` на Cloudflare (его адрес в `backend.base_url`) и GitHub App, установленный на репозиторий. В Worker заданы `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` (секрет) и `ALLOWED_DOMAINS`. Авторам нужен аккаунт GitHub с доступом на запись в репозиторий.

Длинное тире в постах запрещено, как и везде: поля админки подсвечивают его ошибкой, а сборка с ним падает.

## Аналитика и IndexNow

- Аналитика выключена, пока пусты `CF_ANALYTICS_TOKEN` (Cloudflare Web Analytics, все страницы) и `YANDEX_METRIKA_ID` (Яндекс.Метрика, только ru) в `build.py`. Впиши значение, и скрипт появится на всех страницах.
- IndexNow: ключ в `INDEXNOW_KEY`, файл ключа кладётся в корень сайта. После каждого деплоя запускай `python3 tools/indexnow.py`.

## Деплой

Сайт рассчитан на `https://www.rentalplanner.io` (константа `SITE` в `build.py`) и живёт на Cloudflare Workers как статика: своего кода у Worker нет, он раздаёт `dist/`. Бесплатного плана хватает с запасом. Настройки в `wrangler.jsonc`.

Первый запуск (один раз, в панели Cloudflare):

1. Workers & Pages → Create → Import a repository → `Diaglyonok/rental-planner-site`, ветка `main`.
2. Имя проекта `rental-planner-site`, как `name` в `wrangler.jsonc`. Команда сборки `python3 build.py`, команда деплоя `npx wrangler deploy` (по умолчанию).
3. Проверить сайт на техническом адресе `rental-planner-site.<аккаунт>.workers.dev`: он закрыт от поиска заголовком из `_headers`.
4. Переключить домен: в DNS удалить запись `www`, которая ведёт на Wix, затем в Worker → Settings → Domains & Routes → Add → Custom Domain добавить `www.rentalplanner.io`. DNS-запись и сертификат Cloudflare создаст сам. Для `rentalplanner.io` без `www` сделать Redirect Rule на `https://www.rentalplanner.io`.

Дальше каждый коммит в `main` (в том числе пост из админки) собирается и выкладывается сам за минуту-две.

Как раздаётся сайт:

- `_redirects`: 301 со старых адресов сайта на Wix (страницы сфер, посты блога, FAQ). Формат понимают Cloudflare Workers, Pages и Netlify;
- `/terms` и `/privacy` отдают `terms.html` и `privacy.html`, адрес без `.html`;
- несуществующий адрес получает ближайший `404.html` со статусом 404: `/de/...` отдаёт немецкую страницу, остальные английскую.

`preview.py` повторяет это локально, кроме редиректов.

После переключения домена с Wix:

- отправить `sitemap.xml` в Google Search Console, Bing Webmaster Tools и Яндекс.Вебмастер, запустить `python3 tools/indexnow.py`;
- если домен за Cloudflare, проверить, что в настройках выключено «Block AI bots» и managed robots.txt, иначе AI-поиск не увидит сайт.
