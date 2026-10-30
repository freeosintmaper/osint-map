# OSINT Map

[![Telegram data pipeline](https://github.com/freeosintmaper/osint-map/actions/workflows/update-events.yml/badge.svg?branch=main)](https://github.com/freeosintmaper/osint-map/actions/workflows/update-events.yml)
[![NASA FIRMS pipeline](https://github.com/freeosintmaper/osint-map/actions/workflows/update-firms.yml/badge.svg?branch=main)](https://github.com/freeosintmaper/osint-map/actions/workflows/update-firms.yml)
[![Validation](https://github.com/freeosintmaper/osint-map/actions/workflows/validate-pr.yml/badge.svg?branch=main)](https://github.com/freeosintmaper/osint-map/actions/workflows/validate-pr.yml)

**Live map:** <https://freeosintmaper.github.io/osint-map/>  
**Repository:** <https://github.com/freeosintmaper/osint-map>  
**Methodology:** [methodology.html](https://freeosintmaper.github.io/osint-map/methodology.html) · **Corrections:** [corrections.html](https://freeosintmaper.github.io/osint-map/corrections.html) · **Changelog:** [CHANGELOG.md](CHANGELOG.md)

[🇷🇺 Русский](#-русский) · [🇺🇦 Українська](#-українська) · [🇬🇧 English](#-english)

---

## 🇷🇺 Русский

### О проекте

**OSINT Map** — интерактивная карта событий, связанных с войной и политической обстановкой в Украине и России. Проект объединяет публичные Telegram-публикации и внешние геоданные в одном интерфейсе, чтобы упростить просмотр источников и сопоставление сообщений.

Карта — инструмент навигации по открытым данным, а не редакция новостей, независимая разведывательная служба или источник подтверждённых в реальном времени фактов.

> **Важно:** отметка на карте не доказывает, что сообщение истинно. Автоматическая метка «Проверено по N каналам» означает только, что система нашла согласующиеся публикации из разных каналов. Каналы могут ссылаться на один первоисточник или повторять чужие сообщения. Всегда открывайте первоисточник и проверяйте контекст.

### Что есть на карте

| Слой | Содержание |
|---|---|
| **Telegram-события** | Сообщения о тревогах, ударах, операциях, наступлениях, инцидентах и политических событиях. Маркеры сгруппированы; карточки содержат источник, дату и доступные медиа. |
| **DeepState** | Внешний геодатасет DeepStateMap с территориальными полигонами. |
| **Project Owl** | Полигоны из публичного архива Project Owl: категории действий сторон, зоны сосредоточения и серая зона. Исторические и служебные папки фильтруются. |
| **Карта автора** | Пользовательские зоны, хранящиеся в Supabase. Чтение доступно публично в рамках настроек проекта; изменение — через авторизацию и политики RLS. |
| **NASA FIRMS** | Спутниковые тепловые аномалии. Тепловая точка может быть пожаром или другим источником тепла и сама по себе не подтверждает удар. |

Также доступны поиск по городу, каналу и тексту; фильтры времени (6 ч, 24 ч, 3 дня, 7 дней и все события); фильтр типов событий; светлая и тёмная темы; режим заливки/контуров и настройка прозрачности полигонов; RU/UA/EN; инструменты рисования, измерения расстояния и удаления фигур; экспорт метаданных событий в GeoJSON.

### Как формируются события

1. Парсер загружает публичные HTML-страницы последних публикаций Telegram-каналов из списка в <code>scripts/parse_telegram.py</code>.
2. Нормализует текст и отбрасывает часть рекламы, сводок, исторических сообщений и публикаций о других конфликтах.
3. Определяет, относится ли публикация к событию, и извлекает тип и населённый пункт. Используются правила и LLM через Cloudflare Workers AI; результаты LLM кэшируются в <code>data/llm_cache.json</code>.
4. Названия населённых пунктов сопоставляются с локальной базой на основе GeoNames и списком алиасов. Контекст публикации используется для различения одноимённых городов и исключения мест, упомянутых только в пояснениях.
5. События группируются по стране, населённому пункту, типу и часу. Поэтому несколько публикаций могут оказаться в одной карточке.
6. Система выполняет автоматическую межканальную сверку. Для статуса «Проверено по N каналам» нужны совпадения места, страны, типа, временного окна и содержательных признаков при отличающихся формулировках. Это не ручная редакционная проверка и не доказательство независимости источников.
7. Итог сохраняется в <code>data/telegram-events.js</code> и публикуется вместе с сайтом через GitHub Pages.

Если LLM недоступна, парсер использует запасные правила. После трёх последовательных ошибок LLM отключается на текущий запуск; если уже есть полноценный опубликованный набор событий, парсер старается не заменять его неполной выгрузкой.

### Геопривязка и точность

По умолчанию координата обозначает **центр населённого пункта**, а не точное место происшествия. Более конкретная гражданская локация может использоваться только при явном упоминании в исходном тексте и наличии проверяемой текстовой цитаты; подробности описаны в [методологии](https://freeosintmaper.github.io/osint-map/methodology.html).

Система не должна выводить точные координаты промышленных, военных или иных чувствительных объектов из косвенных описаний. Название региона без надёжно определённого города может приводить к региональному fallback. Геокодинг, классификация и автоматическая сверка могут ошибаться; отсутствие маркера также не означает отсутствия события.

### Источники

В парсер включены 26 публичных Telegram-каналов (список и классификация каналов находятся в <code>scripts/parse_telegram.py</code>):

- **Украина:** <code>GeneralStaffZSU</code>, <code>operativnoZSU</code>, <code>ukrpravda_news</code>, <code>uniannet</code>, <code>DeepStateUA</code>, <code>OsintFlow</code>, <code>kharkiv_typical</code>, <code>dnepr_typical</code>, <code>odesa_typical</code>, <code>kherson_typical</code>, <code>donbass_realii</code>, <code>kyivindependent_official</code>, <code>exilenova_plus</code>, <code>supernova_plus</code>.
- **OSINT:** <code>informnapalm</code>, <code>astrapress</code>, <code>bazabazon</code>.
- **Россия:** <code>rybar</code>, <code>voenkorKotenok</code>, <code>wargonzo</code>, <code>readovkanews</code>, <code>lost_armour</code>, <code>boris_rozhin</code>, <code>epoddubny</code>, <code>RVvoenkor</code>, <code>dva_majors</code>.

Внешние геоданные: [DeepStateMap](https://deepstatemap.live/) и [его публичный набор данных](https://github.com/cyterat/deepstate-map-data), [архив Project Owl](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) и [GeoNames](https://www.geonames.org/).

Источники имеют разные стандарты публикации и редакционные позиции. Их наличие на карте не означает одобрения или подтверждения со стороны проекта.

### Обновление данных

Расписания указаны в **UTC** и настроены в GitHub Actions:

| Данные | Расписание в workflow | Что запускается |
|---|---|---|
| Telegram-события | <code>5,35 * * * *</code> | Два запланированных запуска в час — на 05-й и 35-й минутах. |
| NASA FIRMS | <code>15 */3 * * *</code> | Один запуск каждые три часа — на 15-й минуте соответствующего часа. |
| Project Owl | При открытии карты | Браузер ищет последний ежедневный KMZ-архив через несколько CDN-зеркал; при сетевой ошибке остаётся последняя локальная копия, если она есть. |
| Зоны автора | При открытии карты | Запрос к Supabase с повторными попытками; при недоступности сервиса используется последний локальный кэш. |

Для Telegram и FIRMS предусмотрен также ручной запуск через вкладку [GitHub Actions](https://github.com/freeosintmaper/osint-map/actions).

**Расписание GitHub Actions не является гарантией точного времени обновления.** GitHub предупреждает, что события <code>schedule</code> могут задерживаться при высокой нагрузке, а часть запусков может быть пропущена. Поэтому карта не является системой real-time оповещения. Подробности: [документация GitHub о scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

### Технологии

- **Frontend:** HTML, CSS и JavaScript без сборщика; [Leaflet](https://leafletjs.com/).
- **Карта и инструменты:** Leaflet.markercluster, Leaflet.draw, polylineDecorator.
- **Обработка Telegram:** Python 3.11, регулярные выражения, [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/).
- **Геоданные:** GeoNames, OpenStreetMap Nominatim для ограниченного уточнения явно названных мест.
- **Хранилище пользовательских зон:** Supabase (PostgreSQL, Auth, Row Level Security).
- **ИИ-помощник зон:** Supabase Edge Function и Gemini; формирует только проверяемые черновики, не сохраняет изменения автоматически.
- **Публикация и автоматизация:** GitHub Pages и GitHub Actions.

### Локальный запуск

Для просмотра фронтенда нужен Python 3 и доступ в интернет к используемым внешним сервисам:

    git clone https://github.com/freeosintmaper/osint-map.git
    cd osint-map
    python3 -m http.server 8000

Откройте <http://localhost:8000>. Не рекомендуется запускать страницу через <code>file://</code>: используйте локальный HTTP-сервер.

**Запуск Telegram-парсера:**

    pip install openai
    export CLOUDFLARE_ACCOUNT_ID="..."
    export CLOUDFLARE_API_TOKEN="..."
    python3 scripts/parse_telegram.py

Для полноценной LLM-классификации нужны Cloudflare account ID и API token. Без них парсер может перейти на правила и regex-fallback, но качество и полнота результата могут отличаться. Скрипт обновляет <code>data/telegram-events.js</code> и <code>data/llm_cache.json</code>.

**Обновление NASA FIRMS локально:**

    export FIRMS_MAP_KEY="..."
    python3 scripts/fetch_firms.py

**Пересборка базы населённых пунктов:**

    python3 scripts/build_settlements.py

Команда загружает исходные выгрузки GeoNames для Украины и России и пересоздаёт <code>data/settlements.js</code>.

### Секреты GitHub Actions

Добавляйте секреты в **Settings → Secrets and variables → Actions**. Не помещайте токены в исходный код и не публикуйте их в Issues.

| Secret | Для чего нужен |
|---|---|
| <code>CLOUDFLARE_ACCOUNT_ID</code> | Account ID Cloudflare Workers AI для Telegram-парсера. |
| <code>CLOUDFLARE_API_TOKEN</code> | Токен API Cloudflare Workers AI. |
| <code>FIRMS_MAP_KEY</code> | API-ключ NASA FIRMS для обновления тепловых аномалий. |
| <code>SUPABASE_ACCESS_TOKEN</code> | Токен управления Supabase для workflow развёртывания ИИ-функции зон. |
| <code>GEMINI_API_KEY</code> | Ключ Gemini, используемый серверной ИИ-функцией зон. |
| <code>ZONE_AI_ALLOWED_EMAILS</code> | Список email, которым разрешено использовать ИИ-помощник зон. |

Настройка ИИ-помощника и развёртывание Edge Function описаны в [docs/zone-ai-setup.md](docs/zone-ai-setup.md). Для работы карты в браузере используются публичные клиентские настройки Supabase; права на чтение и запись должны ограничиваться политиками RLS. Секреты администрирования Supabase и ключ Gemini нельзя добавлять во frontend.

### Проверки перед Pull Request

    python3 -m py_compile scripts/parse_telegram.py scripts/classify_llm.py scripts/fetch_firms.py
    python3 scripts/test_event_context_verification.py

Для Edge Function дополнительно используется <code>deno check supabase/functions/zone-assistant/index.ts</code>. В CI проверяются синтаксис Python, функция Supabase, регрессионные тесты геопривязки/сверки и синтаксис встроенного JavaScript.

### Структура репозитория

    .
    ├── index.html
    ├── sw.js
    ├── manifest.json
    ├── data/
    │   ├── telegram-events.js
    │   ├── firms-fires.json
    │   ├── settlements.js
    │   ├── llm_cache.json
    │   └── osm_geocode_cache.json
    ├── scripts/
    │   ├── parse_telegram.py
    │   ├── classify_llm.py
    │   ├── build_settlements.py
    │   ├── fetch_firms.py
    │   └── test_event_context_verification.py
    ├── lib/
    ├── supabase/functions/zone-assistant/
    ├── docs/zone-ai-setup.md
    └── .github/workflows/
        ├── update-events.yml
        ├── update-firms.yml
        ├── deploy-zone-ai.yml
        └── validate-pr.yml

### Как сообщить об ошибке или помочь

- Для неправильной геопривязки или данных используйте страницу [исправлений](https://freeosintmaper.github.io/osint-map/corrections.html).
- Для ошибок приложения и предложений создайте [GitHub Issue](https://github.com/freeosintmaper/osint-map/issues).
- Изменения кода отправляйте через Pull Request. Перед отправкой запустите проверки из раздела выше.

### Лицензии и ограничения

Код проекта распространяется по лицензии [MIT](LICENSE). Компиляция и оригинальные метаданные экспорта регулируются [CC BY 4.0](LICENSE-DATA.md) только в той мере, в какой права на них принадлежат проекту. Права на публикации Telegram, медиа и сторонние геоданные остаются у их правообладателей и регулируются условиями первоисточников.

Карта предоставляется «как есть», без гарантии полноты, точности или доступности внешних сервисов. Не используйте её как единственный источник для важных решений, военного планирования или наведения. Проверяйте первоисточники и учитывайте время публикации.

---

## 🇺🇦 Українська

### Про проєкт

**OSINT Map** — інтерактивна карта подій, пов’язаних із війною та політичною ситуацією в Україні й Росії. Проєкт поєднує публікації з відкритих Telegram-каналів і зовнішні геодані в одному інтерфейсі.

Це інструмент для перегляду відкритих даних, а не редакція новин і не джерело гарантовано підтверджених фактів.

> **Важливо:** позначка на карті не доводить правдивість повідомлення. «Перевірено за N каналами» — це результат автоматичного зіставлення публікацій із різних каналів. Вони можуть посилатися на одне першоджерело або повторювати чужі повідомлення. Перевіряйте оригінальну публікацію та її контекст.

### Шари та функції

- **Telegram-події:** повітряні тривоги, удари, операції, наступи, інциденти й політичні події; кластери маркерів, картки джерел і доступні медіа.
- **DeepState:** зовнішній геодатасет із полігонами територій.
- **Project Owl:** полігони з публічного архіву, розподілені за категоріями; історичні та службові папки фільтруються.
- **Карта автора:** користувацькі зони в Supabase; редагування доступне після авторизації та перевіряється політиками RLS.
- **NASA FIRMS:** супутникові теплові аномалії. Теплова точка не є самостійним доказом удару.
- Пошук за містом, каналом і текстом; фільтри часу й типу події; теми, прозорість і контури полігонів; RU/UA/EN; малювання, вимірювання відстані та експорт метаданих подій у GeoJSON.

### Обробка й геоприв’язка

Парсер отримує публічні сторінки Telegram, відсіює частину реклами, зведень, історичних повідомлень та інших конфліктів, а потім визначає тип події й населені пункти за допомогою правил і LLM Cloudflare Workers AI. Назви звіряються з базою GeoNames та списком аліасів. Повідомлення можуть об’єднуватися за країною, місцем, типом і годиною.

Автоматична міжканальна перевірка враховує збіг місця, країни, типу, часу й змістових ознак та відмінність формулювань. Це не редакційна перевірка й не доказ незалежності джерел. Докладно: [методологія](https://freeosintmaper.github.io/osint-map/methodology.html).

За замовчуванням координати позначають **центр населеного пункту**, а не точне місце події. Точніше уточнення можливе лише за явної текстової згадки та перевірюваної цитати. Система не повинна виводити точні координати чутливих промислових чи військових об’єктів із непрямих описів.

### Джерела та оновлення

До парсера включено 26 публічних Telegram-каналів. Їхній актуальний список і класифікація містяться в <code>scripts/parse_telegram.py</code>. Зовнішні джерела: [DeepStateMap](https://deepstatemap.live/), [DeepState data](https://github.com/cyterat/deepstate-map-data), [Project Owl](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) та [GeoNames](https://www.geonames.org/).

Розклади GitHub Actions задаються в UTC:

| Дані | Cron | Частота |
|---|---|---|
| Telegram | <code>5,35 * * * *</code> | Двічі на годину |
| NASA FIRMS | <code>15 */3 * * *</code> | Раз на три години |
| Project Owl | Під час відкриття карти | Щоденний KMZ через кілька CDN-дзеркал; за потреби — локальний кеш |
| Зони автора | Під час відкриття карти | Supabase із повторними спробами та локальним кешем |

GitHub попереджає, що заплановані запуски можуть затримуватися або пропускатися під час високого навантаження. Тому це не система сповіщень у реальному часі. Див. [документацію GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

### Локальний запуск

Потрібні Git, Python 3 та інтернет-з’єднання:

    git clone https://github.com/freeosintmaper/osint-map.git
    cd osint-map
    python3 -m http.server 8000

Відкрийте <http://localhost:8000>.

Для Telegram-парсера встановіть <code>openai</code> і задайте <code>CLOUDFLARE_ACCOUNT_ID</code> та <code>CLOUDFLARE_API_TOKEN</code>, потім виконайте <code>python3 scripts/parse_telegram.py</code>. Без доступу до LLM використовується запасна обробка правилами, тому результат може відрізнятися.

Для NASA FIRMS потрібен <code>FIRMS_MAP_KEY</code> і команда <code>python3 scripts/fetch_firms.py</code>. База населених пунктів створюється через <code>python3 scripts/build_settlements.py</code>.

Секрети GitHub Actions: <code>CLOUDFLARE_ACCOUNT_ID</code>, <code>CLOUDFLARE_API_TOKEN</code>, <code>FIRMS_MAP_KEY</code>; для розгортання ІІ-помічника зон — <code>SUPABASE_ACCESS_TOKEN</code>, <code>GEMINI_API_KEY</code>, <code>ZONE_AI_ALLOWED_EMAILS</code>. Інструкція: [docs/zone-ai-setup.md](docs/zone-ai-setup.md). Не додавайте секрети у код або frontend.

### Розробка, ліцензії та зворотний зв’язок

Перевірки:

    python3 -m py_compile scripts/parse_telegram.py scripts/classify_llm.py scripts/fetch_firms.py
    python3 scripts/test_event_context_verification.py

Код — [MIT](LICENSE). Умови для компіляції та оригінальних метаданих експорту — [CC BY 4.0](LICENSE-DATA.md) у межах прав проєкту; сторонні публікації, медіа й геодані залишаються під умовами їхніх правовласників.

Повідомити про помилку можна на сторінці [виправлень](https://freeosintmaper.github.io/osint-map/corrections.html) або через [GitHub Issues](https://github.com/freeosintmaper/osint-map/issues). Карта не гарантує повноти чи точності, не призначена для військового планування або наведення. Перевіряйте першоджерела.

---

## 🇬🇧 English

### About

**OSINT Map** is an interactive map of events related to the war and political developments in Ukraine and Russia. It brings together public Telegram posts and external geospatial datasets in one interface.

The project is a tool for browsing open information, not a newsroom, an independent intelligence service, or a source of guaranteed real-time facts.

> **Important:** a marker does not prove that a report is true. “Verified by N channels” is an automated cross-channel consistency label. Different channels may rely on the same original source or repeat one another. Always open and assess the source post.

### Map layers and features

- **Telegram events:** air-raid alerts, strikes, operations, offensives, incidents, and political developments, with clustered markers, source cards, dates, and available media.
- **DeepState:** an external geospatial dataset containing territorial polygons.
- **Project Owl:** polygons from the public archive, grouped into map categories; historical and administrative folders are filtered out.
- **Author zones:** user-managed polygons stored in Supabase. Editing requires authentication and is governed by RLS policies.
- **NASA FIRMS:** satellite thermal anomalies. A hotspot may be a fire or another heat source and is not proof of a strike.
- Search by settlement, channel, and text; time and event-type filters; light/dark themes; polygon opacity and outline modes; RU/UA/EN interface; drawing and distance measurement tools; GeoJSON export of event metadata.

### Processing and geolocation

The parser fetches public Telegram channel pages, filters some advertising, summaries, historical posts, and unrelated conflicts, then classifies candidate events and extracts place names using rules and Cloudflare Workers AI. Place names are matched against a GeoNames-based local database and an alias list. Events may be grouped by country, settlement, type, and hour.

Automated cross-source checking looks for matching country, place, event type, time window, shared content clues, and distinct wording across channels. It is not editorial fact-checking and does not establish source independence. See the full [methodology](https://freeosintmaper.github.io/osint-map/methodology.html).

By default, coordinates represent the **centre of a settlement**, not the exact incident location. More specific geolocation is only considered when explicitly stated in the source text and supported by a checkable quote. The system should not infer precise coordinates of sensitive military or industrial facilities from indirect descriptions.

### Sources and update schedule

The parser currently includes 26 public Telegram channels; the maintained list and channel labels are in <code>scripts/parse_telegram.py</code>. External sources include [DeepStateMap](https://deepstatemap.live/), [its public data feed](https://github.com/cyterat/deepstate-map-data), the [Project Owl archive](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), and [GeoNames](https://www.geonames.org/).

GitHub Actions schedules are in UTC:

| Data | Cron | Intended frequency |
|---|---|---|
| Telegram events | <code>5,35 * * * *</code> | Twice per hour |
| NASA FIRMS | <code>15 */3 * * *</code> | Every three hours |
| Project Owl | On page load | Latest daily KMZ via multiple CDN mirrors; local cache fallback |
| Author zones | On page load | Supabase with retries and a local cache fallback |

GitHub notes that scheduled workflows may be delayed or dropped during periods of high load. The map is therefore not a real-time alerting system. See [GitHub's scheduled workflow documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

### Run locally

Requirements: Git, Python 3, and internet access.

    git clone https://github.com/freeosintmaper/osint-map.git
    cd osint-map
    python3 -m http.server 8000

Open <http://localhost:8000>.

To run the Telegram parser, install <code>openai</code>, set <code>CLOUDFLARE_ACCOUNT_ID</code> and <code>CLOUDFLARE_API_TOKEN</code>, then run <code>python3 scripts/parse_telegram.py</code>. If the LLM is unavailable, the parser falls back to rule-based matching, which may produce different results.

NASA FIRMS updates require <code>FIRMS_MAP_KEY</code> and <code>python3 scripts/fetch_firms.py</code>. Rebuild the settlement database with <code>python3 scripts/build_settlements.py</code>.

GitHub Actions secrets: <code>CLOUDFLARE_ACCOUNT_ID</code>, <code>CLOUDFLARE_API_TOKEN</code>, and <code>FIRMS_MAP_KEY</code>. Deploying the zone AI assistant additionally requires <code>SUPABASE_ACCESS_TOKEN</code>, <code>GEMINI_API_KEY</code>, and <code>ZONE_AI_ALLOWED_EMAILS</code>; see [docs/zone-ai-setup.md](docs/zone-ai-setup.md). Never commit secrets or put administrative credentials in frontend code.

### Development, licensing, and feedback

Run the checks:

    python3 -m py_compile scripts/parse_telegram.py scripts/classify_llm.py scripts/fetch_firms.py
    python3 scripts/test_event_context_verification.py

Source code is licensed under [MIT](LICENSE). The project's compilation and original export metadata are covered by [CC BY 4.0](LICENSE-DATA.md) only to the extent that the project owns the relevant rights. Third-party posts, media, and geospatial data remain subject to their respective owners' terms.

Report data issues via the [corrections page](https://freeosintmaper.github.io/osint-map/corrections.html) or open a [GitHub Issue](https://github.com/freeosintmaper/osint-map/issues). The map does not guarantee completeness or accuracy and is not intended for military planning or targeting. Check the original sources.

---

## Contacts

- [GitHub Issues](https://github.com/freeosintmaper/osint-map/issues) — bugs and suggestions.
- [Pull Requests](https://github.com/freeosintmaper/osint-map/pulls) — code and documentation contributions are welcome.
