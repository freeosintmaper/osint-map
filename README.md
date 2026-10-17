# OSINT-карта · OSINT-карта · OSINT Map

[🇷🇺 Русский](#-русский) · [🇺🇦 Українська](#-українська) · [🇬🇧 English](#-english)

**Сайт:** https://freeosintmaper.github.io/osint-map/
**Репозиторий:** https://github.com/freeosintmaper/osint-map

---

## 🇷🇺 Русский

### Что это

Интерактивная карта военных и политических событий на территории Украины и России, собранная из открытых источников.

OSINT-карта агрегирует данные из Telegram-каналов, спутниковых снимков и публичных карт контроля территорий. В отличие от новостных лент, здесь события привязаны к координатам и отфильтрованы от шума: реклама, аналитика, исторические справки и посты про другие конфликты не попадают на карту.

Цель — дать быстрый обзор актуальной обстановки без чтения десятков каналов вручную.

### Возможности

**Слои карты:**

- **Территория РФ** — данные DeepStateMap (актуальный контроль территорий)
- **Project Owl** — 4 категории зон (действия РФ, действия ВСУ, места сосредоточения, серая зона). Исторические полигоны 2014/2022 отфильтрованы
- **Карта автора** — пользовательские зоны контроля (Supabase, редактирование через админ-панель)
- **NASA FIRMS** — тепловые аномалии и пожары
- **События из Telegram** — маркеры с кластеризацией, popup-карточки с медиа и ссылкой на источник

**Фильтры и настройки:**

- Быстрые фильтры времени: 6ч / 24ч / 3д / 7д / Всё (по умолчанию — 24 часа)
- Поиск по городу, каналу, тексту
- Фильтр по типу события: тревога, удар, операция, наступление, инцидент, политика
- Прозрачность и режим отображения (заливка / контуры) для всех полигональных слоёв
- Светлая и тёмная тема с сохранением выбора и автоопределением системной темы
- i18n: RU / UA / EN
- Компактная сворачиваемая легенда

**Инструменты:**

- Маркер, линия, стрелка, полигон, прямоугольник, круг
- Измерение расстояний
- Ластик — удаление отдельных фигур
- Очистка всех рисунков
- Импорт/экспорт KML и GeoJSON

**Админ-функции:**

- Вход через Supabase Auth (email + пароль)
- Редактирование зон контроля (рисование полигонов, изменение вершин, удаление)
- RLS-политики: чтение — всем, запись — только авторизованным

### Архитектура

```
Telegram-каналы (26 шт.)
       │
       ▼
Python-парсер ──── LLM (Cloudflare Workers AI)
       │              классификация и геокодинг
       ▼
data/telegram-events.js   (JSON в JS-обёртке)
       │
       ▼
GitHub Pages ──── Leaflet.js ──── Supabase (зоны автора)
```

**Парсер** запускается через GitHub Actions каждые 15 минут (`cron: '5,20,35,50 * * * *'`):

1. Загружает HTML последних постов каждого канала через `t.me/s/<channel>`
2. Отсеивает рекламу, сводки, исторические посты, иностранные конфликты
3. Отправляет остальные посты в LLM (Cloudflare Workers AI, модель `llama-3.1-8b-instruct-fast`)
4. LLM возвращает JSON: является ли пост событием, тип, список локаций с указанием страны (UA/RU)
5. Геокодинг: названия сопоставляются с базой GeoNames (386 570 населённых пунктов) и ручным списком алиасов (~300 городов)
6. Дедупликация: одинаковые события из разных каналов схлопываются по принципу «локация + тип + час»
7. Результат записывается в `data/telegram-events.js` и коммитится в репозиторий
8. GitHub Pages автоматически обновляет сайт

**Почему LLM, а не regex.** Первая версия парсера использовала только регулярные выражения. Это приводило к массе ложных срабатываний: «Житель», «Лесной», «Мирный» (слова, совпадающие с названиями посёлков), «Брянская область» (регион, а не город), «Днепропетровской области» (не даёт конкретной точки), исторические посты (2014–2022) не отличить от актуальных без понимания контекста. LLM решает это за счёт понимания контекста. Regex-фильтры остаются как дешёвый предфильтр и fallback на случай недоступности LLM.

### Стек

| Слой | Технология |
|------|------------|
| Фронтенд | Чистый HTML/JS + Leaflet.js |
| Кластеризация | Leaflet.markercluster |
| Рисование | Leaflet.draw + polylineDecorator |
| Карты | Esri World Street Map (светлая), CSS-фильтр (тёмная) |
| База данных | Supabase (PostgreSQL + Auth + RLS) |
| Парсер | Python 3.11 |
| LLM | Cloudflare Workers AI |
| Деплой | GitHub Pages |
| Обновление данных | GitHub Actions (cron каждые 15 минут) |

Всё работает бесплатно — без платных подписок и API-ключей, требующих карты.

### Источники данных

**Telegram-каналы (26):**

- **Украина:** `GeneralStaffZSU`, `operativnoZSU`, `ukrpravda_news`, `uniannet`, `DeepStateUA`, `OsintFlow`, `kharkiv_typical`, `dnepr_typical`, `odesa_typical`, `kherson_typical`, `donbass_realii`, `kyivindependent_official`, `exilenova_plus`, `supernova_plus`
- **OSINT:** `informnapalm`, `astrapress`, `bazabazon`
- **Россия:** `rybar`, `voenkorKotenok`, `wargonzo`, `readovkanews`, `lost_armour`, `boris_rozhin`, `epoddubny`, `RVvoenkor`, `dva_majors`

**Внешние слои:** [DeepStateMap](https://deepstatemap.live/), [Project Owl](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), [GeoNames](https://www.geonames.org/).

### Локальный запуск

**Фронтенд** — достаточно открыть `index.html` через статический сервер:

```bash
python3 -m http.server 8000
# открыть http://localhost:8000
```

Данные (`data/telegram-events.js`, `data/firms-fires.json`) уже закоммичены.

**Парсер:**

```bash
pip install openai
export CLOUDFLARE_ACCOUNT_ID="..."
export CLOUDFLARE_API_TOKEN="..."
python3 scripts/parse_telegram.py
```

Результат — `data/telegram-events.js`.

### Переменные окружения (GitHub Secrets)

| Секрет | Назначение |
|--------|------------|
| `CLOUDFLARE_ACCOUNT_ID` | ID аккаунта Cloudflare (Workers AI) |
| `CLOUDFLARE_API_TOKEN` | API-токен для Workers AI |

**Как получить:**

1. Регистрация на https://dash.cloudflare.com (бесплатно, без карты)
2. Раздел **AI → Workers AI → Use REST API → Create API Token**
3. Скопировать `Account ID` и сгенерированный токен
4. В GitHub: `Settings → Secrets and variables → Actions → New repository secret`

### Структура репозитория

```
.
├── index.html                    # Фронтенд (карта)
├── icon.svg                      # Иконка сайта
├── manifest.json                 # PWA-манифест
├── data/
│   ├── telegram-events.js        # События (генерируется парсером)
│   ├── firms-fires.json          # Пожары NASA FIRMS
│   ├── settlements.js            # База НП (386 570 записей)
│   └── llm_cache.json            # Кэш LLM (коммитится в git)
├── scripts/
│   ├── parse_telegram.py         # Основной парсер
│   ├── classify_llm.py           # Модуль LLM-классификации
│   └── build_settlements.py      # Сборка базы GeoNames
├── lib/                          # Leaflet, markercluster, draw и т.д.
└── .github/workflows/
    └── update-events.yml         # Cron-обновление данных
```

### Ограничения и известные проблемы

- **Задержка обновления**: данные обновляются каждые 15 минут, не в реальном времени. Для оперативных нужд используйте первоисточники.
- **Точность геокодинга**: LLM определяет локации по тексту поста. Ошибки возможны (особенно при дублирующихся топонимах — например, Новомосковск в РФ и Украине). Для критических случаев страна определяется из контекста поста.
- **Лимит LLM**: Cloudflare Workers AI даёт 10 000 Neurons/день бесплатно. Один запрос ≈ 10 Neurons, то есть ~1000 запросов/день. Благодаря кэшу (`data/llm_cache.json`) повторные посты в LLM не отправляются — реальный расход 200–300 запросов/день, запас ~3×.
- **Дублирование новостей**: если один и тот же факт публикуют в разных каналах, дедупликация по (локация + тип + час) схлопывает их в одно событие. Иногда это приводит к объединению двух разных событий.

### Дорожная карта

- [x] Multi-location (одно событие → несколько точек)
- [x] LLM-классификация через Cloudflare Workers AI
- [x] Дедупликация по (локация, тип, час)
- [x] Панель настроек справа
- [x] Тёмная тема с CSS-фильтром
- [x] Фильтры-чипы времени (6ч/24ч/3д/7д/Всё)
- [ ] Автоочистка старых событий (7+ дней)
- [ ] Таймлапс — просмотр карты на дату в прошлом
- [ ] Артиллерийский калькулятор (радиусы HIMARS/M777 и др.)
- [ ] Экспорт событий в GeoJSON
- [ ] Улучшенные попапы с медиа-превью

### Лицензия

Код проекта распространяется под лицензией [MIT](LICENSE). Проект использует открытые данные из публичных источников — Telegram-каналов, DeepStateMap, Project Owl, NASA FIRMS, GeoNames. Условия использования этих данных определяются их первоисточниками.

**Важно:** карта не является инструментом военного планирования и не даёт гарантий точности. Все данные — это агрегация публичных сообщений, требующая независимой проверки.

---

## 🇺🇦 Українська

### Що це

Інтерактивна карта воєнних і політичних подій на території України та Росії, зібрана з відкритих джерел.

OSINT-карта агрегує дані з Telegram-каналів, супутникових знімків і публічних карт контролю територій. На відміну від новинних стрічок, тут події прив'язані до координат і відфільтровані від шуму: реклама, аналітика, історичні довідки та пости про інші конфлікти не потрапляють на карту.

Мета — дати швидкий огляд актуальної обстановки без читання десятків каналів вручну.

### Можливості

**Шари карти:**

- **Територія РФ** — дані DeepStateMap (актуальний контроль територій)
- **Project Owl** — 4 категорії зон (дії РФ, дії ЗСУ, місця зосередження, сіра зона). Історичні полігони 2014/2022 відфільтровані
- **Карта автора** — користувацькі зони контролю (Supabase, редагування через адмін-панель)
- **NASA FIRMS** — теплові аномалії та пожежі
- **Події з Telegram** — маркери з кластеризацією, popup-картки з медіа та посиланням на джерело

**Фільтри та налаштування:**

- Швидкі фільтри часу: 6г / 24г / 3д / 7д / Все (за замовчуванням — 24 години)
- Пошук за містом, каналом, текстом
- Фільтр за типом події: тривога, удар, операція, наступ, інцидент, політика
- Прозорість і режим відображення (заливка / контури) для всіх полігональних шарів
- Світла та темна тема зі збереженням вибору та автовизначенням системної теми
- i18n: RU / UA / EN
- Компактна згортувана легенда

**Інструменти:**

- Маркер, лінія, стрілка, полігон, прямокутник, коло
- Вимірювання відстаней
- Ластик — видалення окремих фігур
- Очищення всіх малюнків
- Імпорт/експорт KML і GeoJSON

**Адмін-функції:**

- Вхід через Supabase Auth (email + пароль)
- Редагування зон контролю (малювання полігонів, зміна вершин, видалення)
- RLS-політики: читання — всім, запис — лише авторизованим

### Архітектура

```
Telegram-канали (26 шт.)
       │
       ▼
Python-парсер ──── LLM (Cloudflare Workers AI)
       │              класифікація та геокодинг
       ▼
data/telegram-events.js   (JSON у JS-обгортці)
       │
       ▼
GitHub Pages ──── Leaflet.js ──── Supabase (зони автора)
```

**Парсер** запускається через GitHub Actions кожні 15 хвилин (`cron: '5,20,35,50 * * * *'`):

1. Завантажує HTML останніх постів кожного каналу через `t.me/s/<channel>`
2. Відсіює рекламу, зведення, історичні пости, іноземні конфлікти
3. Надсилає решту постів у LLM (Cloudflare Workers AI, модель `llama-3.1-8b-instruct-fast`)
4. LLM повертає JSON: чи є пост подією, тип, список локацій із зазначенням країни (UA/RU)
5. Геокодинг: назви зіставляються з базою GeoNames (386 570 населених пунктів) і ручним списком аліасів (~300 міст)
6. Дедуплікація: однакові події з різних каналів згортаються за принципом «локація + тип + година»
7. Результат записується в `data/telegram-events.js` і комітиться в репозиторій
8. GitHub Pages автоматично оновлює сайт

**Чому LLM, а не regex.** Перша версія парсера використовувала лише регулярні вирази. Це призводило до маси хибних спрацювань: «Житель», «Лесной», «Мирный» (слова, що збігаються з назвами поселень), «Брянская область» (регіон, а не місто), «Днепропетровской области» (не дає конкретної точки), історичні пости (2014–2022) не відрізнити від актуальних без розуміння контексту. LLM вирішує це завдяки розумінню контексту. Regex-фільтри залишаються як дешевий префільтр і fallback на випадок недоступності LLM.

### Стек

| Шар | Технологія |
|------|------------|
| Фронтенд | Чистий HTML/JS + Leaflet.js |
| Кластеризація | Leaflet.markercluster |
| Малювання | Leaflet.draw + polylineDecorator |
| Карти | Esri World Street Map (світла), CSS-фільтр (темна) |
| База даних | Supabase (PostgreSQL + Auth + RLS) |
| Парсер | Python 3.11 |
| LLM | Cloudflare Workers AI |
| Деплой | GitHub Pages |
| Оновлення даних | GitHub Actions (cron кожні 15 хвилин) |

Все працює безкоштовно — без платних підписок і API-ключів, що потребують картки.

### Джерела даних

**Telegram-канали (26):**

- **Україна:** `GeneralStaffZSU`, `operativnoZSU`, `ukrpravda_news`, `uniannet`, `DeepStateUA`, `OsintFlow`, `kharkiv_typical`, `dnepr_typical`, `odesa_typical`, `kherson_typical`, `donbass_realii`, `kyivindependent_official`, `exilenova_plus`, `supernova_plus`
- **OSINT:** `informnapalm`, `astrapress`, `bazabazon`
- **Росія:** `rybar`, `voenkorKotenok`, `wargonzo`, `readovkanews`, `lost_armour`, `boris_rozhin`, `epoddubny`, `RVvoenkor`, `dva_majors`

**Зовнішні шари:** [DeepStateMap](https://deepstatemap.live/), [Project Owl](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), [GeoNames](https://www.geonames.org/).

### Локальний запуск

**Фронтенд** — достатньо відкрити `index.html` через статичний сервер:

```bash
python3 -m http.server 8000
# відкрити http://localhost:8000
```

Дані (`data/telegram-events.js`, `data/firms-fires.json`) вже закомічені.

**Парсер:**

```bash
pip install openai
export CLOUDFLARE_ACCOUNT_ID="..."
export CLOUDFLARE_API_TOKEN="..."
python3 scripts/parse_telegram.py
```

Результат — `data/telegram-events.js`.

### Змінні середовища (GitHub Secrets)

| Секрет | Призначення |
|--------|-------------|
| `CLOUDFLARE_ACCOUNT_ID` | ID акаунта Cloudflare (Workers AI) |
| `CLOUDFLARE_API_TOKEN` | API-токен для Workers AI |

**Як отримати:**

1. Реєстрація на https://dash.cloudflare.com (безкоштовно, без картки)
2. Розділ **AI → Workers AI → Use REST API → Create API Token**
3. Скопіювати `Account ID` і згенерований токен
4. У GitHub: `Settings → Secrets and variables → Actions → New repository secret`

### Структура репозиторію

```
.
├── index.html                    # Фронтенд (карта)
├── icon.svg                      # Іконка сайту
├── manifest.json                 # PWA-манифест
├── data/
│   ├── telegram-events.js        # Події (генерується парсером)
│   ├── firms-fires.json          # Пожежі NASA FIRMS
│   ├── settlements.js            # База НП (386 570 записів)
│   └── llm_cache.json            # Кеш LLM (комітиться в git)
├── scripts/
│   ├── parse_telegram.py         # Основний парсер
│   ├── classify_llm.py           # Модуль LLM-класифікації
│   └── build_settlements.py      # Складання бази GeoNames
├── lib/                          # Leaflet, markercluster, draw тощо
└── .github/workflows/
    └── update-events.yml         # Cron-оновлення даних
```

### Обмеження та відомі проблеми

- **Затримка оновлення**: дані оновлюються кожні 15 хвилин, не в реальному часі. Для оперативних потреб використовуйте першоджерела.
- **Точність геокодингу**: LLM визначає локації за текстом поста. Помилки можливі (особливо при дубльованих топонімах — наприклад, Новомосковськ у РФ та Україні). Для критичних випадків країна визначається з контексту поста.
- **Ліміт LLM**: Cloudflare Workers AI дає 10 000 Neurons/день безкоштовно. Один запит ≈ 10 Neurons, тобто ~1000 запитів/день. Завдяки кешу (`data/llm_cache.json`) повторні пости в LLM не надсилаються — реальна витрата 200–300 запитів/день, запас ~3×.
- **Дублювання новин**: якщо один і той самий факт публікують у різних каналах, дедуплікація за (локація + тип + година) згортає їх в одну подію. Іноді це призводить до об'єднання двох різних подій.

### Дорожня карта

- [x] Multi-location (одна подія → кілька точок)
- [x] LLM-класифікація через Cloudflare Workers AI
- [x] Дедуплікація за (локація, тип, година)
- [x] Панель налаштувань праворуч
- [x] Темна тема з CSS-фільтром
- [x] Фільтри-чипи часу (6г/24г/3д/7д/Все)
- [ ] Автоочищення старих подій (7+ днів)
- [ ] Таймлапс — перегляд карти на дату в минулому
- [ ] Артилерійський калькулятор (радіуси HIMARS/M777 тощо)
- [ ] Експорт подій у GeoJSON
- [ ] Покращені попапи з медіа-прев'ю

### Ліцензія

Код проєкту розповсюджується під ліцензією [MIT](LICENSE). Проєкт використовує відкриті дані з публічних джерел — Telegram-каналів, DeepStateMap, Project Owl, NASA FIRMS, GeoNames. Умови використання цих даних визначаються їхніми першоджерелами.

**Важливо:** карта не є інструментом воєнного планування і не дає гарантій точності. Всі дані — це агрегація публічних повідомлень, що потребує незалежної перевірки.

---

## 🇬🇧 English

### What it is

An interactive map of military and political events in Ukraine and Russia, aggregated from open sources.

The OSINT map pulls data from Telegram channels, satellite imagery, and public territory-control maps. Unlike news feeds, events here are tied to coordinates and filtered from noise: ads, analysis, historical references, and posts about other conflicts do not appear on the map.

The goal is to provide a quick overview of the current situation without manually reading dozens of channels.

### Features

**Map layers:**

- **Territory held by RF** — DeepStateMap data (current territory control)
- **Project Owl** — 4 zone categories (Russian actions, Ukrainian actions, holding areas, grey zone). Historical polygons from 2014/2022 are filtered out
- **Author's map** — user-defined control zones (Supabase, edited via admin panel)
- **NASA FIRMS** — thermal anomalies and fires
- **Telegram events** — clustered markers, popup cards with media and source link

**Filters and settings:**

- Quick time filters: 6h / 24h / 3d / 7d / All (default — 24 hours)
- Search by city, channel, text
- Filter by event type: air raid alert, strike, operation, offensive, incident, politics
- Opacity and display mode (fill / outline) for all polygon layers
- Light and dark themes with preference persistence and system theme detection
- i18n: RU / UA / EN
- Compact collapsible legend

**Tools:**

- Marker, line, arrow, polygon, rectangle, circle
- Distance measurement
- Eraser — delete individual shapes
- Clear all drawings
- Import/export KML and GeoJSON

**Admin features:**

- Login via Supabase Auth (email + password)
- Editing control zones (draw polygons, modify vertices, delete)
- RLS policies: read — public, write — authenticated only

### Architecture

```
Telegram channels (26)
       │
       ▼
Python parser ──── LLM (Cloudflare Workers AI)
       │              classification and geocoding
       ▼
data/telegram-events.js   (JSON wrapped in JS)
       │
       ▼
GitHub Pages ──── Leaflet.js ──── Supabase (author zones)
```

The **parser** runs via GitHub Actions every 15 minutes (`cron: '5,20,35,50 * * * *'`):

1. Fetches the HTML of each channel's latest posts via `t.me/s/<channel>`
2. Filters out ads, summaries, historical posts, foreign conflicts
3. Sends the remaining posts to the LLM (Cloudflare Workers AI, model `llama-3.1-8b-instruct-fast`)
4. LLM returns JSON: whether the post is an event, its type, list of locations with country (UA/RU)
5. Geocoding: names are matched against the GeoNames database (386,570 settlements) and a manual alias list (~300 cities)
6. Deduplication: identical events from different channels collapse by "location + type + hour"
7. Result is written to `data/telegram-events.js` and committed to the repository
8. GitHub Pages automatically updates the site

**Why LLM, not regex.** The first parser version used only regular expressions. This led to many false positives: "Житель", "Лесной", "Мирный" (words matching settlement names), "Брянская область" (a region, not a city), "Днепропетровской области" (no specific point), historical posts (2014–2022) cannot be distinguished from current ones without context understanding. LLM solves this through context understanding. Regex filters remain as a cheap pre-filter and fallback in case the LLM is unavailable.

### Stack

| Layer | Technology |
|-------|------------|
| Frontend | Pure HTML/JS + Leaflet.js |
| Clustering | Leaflet.markercluster |
| Drawing | Leaflet.draw + polylineDecorator |
| Maps | Esri World Street Map (light), CSS filter (dark) |
| Database | Supabase (PostgreSQL + Auth + RLS) |
| Parser | Python 3.11 |
| LLM | Cloudflare Workers AI |
| Deploy | GitHub Pages |
| Data updates | GitHub Actions (cron every 15 minutes) |

Everything runs for free — no paid subscriptions, no API keys requiring a credit card.

### Data sources

**Telegram channels (26):**

- **Ukraine:** `GeneralStaffZSU`, `operativnoZSU`, `ukrpravda_news`, `uniannet`, `DeepStateUA`, `OsintFlow`, `kharkiv_typical`, `dnepr_typical`, `odesa_typical`, `kherson_typical`, `donbass_realii`, `kyivindependent_official`, `exilenova_plus`, `supernova_plus`
- **OSINT:** `informnapalm`, `astrapress`, `bazabazon`
- **Russia:** `rybar`, `voenkorKotenok`, `wargonzo`, `readovkanews`, `lost_armour`, `boris_rozhin`, `epoddubny`, `RVvoenkor`, `dva_majors`

**External layers:** [DeepStateMap](https://deepstatemap.live/), [Project Owl](https://github.com/owlmaps/UAControlMapBackups), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), [GeoNames](https://www.geonames.org/).

### Local run

**Frontend** — just open `index.html` via any static server:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

Data (`data/telegram-events.js`, `data/firms-fires.json`) is already committed.

**Parser:**

```bash
pip install openai
export CLOUDFLARE_ACCOUNT_ID="..."
export CLOUDFLARE_API_TOKEN="..."
python3 scripts/parse_telegram.py
```

Result — `data/telegram-events.js`.

### Environment variables (GitHub Secrets)

| Secret | Purpose |
|--------|---------|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (Workers AI) |
| `CLOUDFLARE_API_TOKEN` | Workers AI API token |

**How to get:**

1. Sign up at https://dash.cloudflare.com (free, no card required)
2. **AI → Workers AI → Use REST API → Create API Token**
3. Copy the `Account ID` and the generated token
4. In GitHub: `Settings → Secrets and variables → Actions → New repository secret`

### Repository structure

```
.
├── index.html                    # Frontend (map)
├── icon.svg                      # Site icon
├── manifest.json                 # PWA manifest
├── data/
│   ├── telegram-events.js        # Events (generated by the parser)
│   ├── firms-fires.json          # NASA FIRMS fires
│   ├── settlements.js            # Settlements database (386,570 records)
│   └── llm_cache.json            # LLM cache (committed to git)
├── scripts/
│   ├── parse_telegram.py         # Main parser
│   ├── classify_llm.py           # LLM classification module
│   └── build_settlements.py      # GeoNames database builder
├── lib/                          # Leaflet, markercluster, draw, etc.
└── .github/workflows/
    └── update-events.yml         # Cron data update
```

### Limitations and known issues

- **Update lag**: data is refreshed every 15 minutes, not in real time. For operational needs, use the original sources.
- **Geocoding accuracy**: the LLM determines locations from post text. Errors are possible (especially with duplicate toponyms — e.g. Novomoskovsk in Russia and Ukraine). For critical cases the country is inferred from the post's context.
- **LLM quota**: Cloudflare Workers AI provides 10,000 Neurons/day for free. One request ≈ 10 Neurons, i.e. ~1,000 requests/day. Thanks to the cache (`data/llm_cache.json`), repeated posts are not sent to the LLM — actual usage is 200–300 requests/day, ~3× headroom.
- **News duplication**: if the same fact is reported by different channels, deduplication by (location + type + hour) collapses them into one event. Occasionally this merges two distinct events.

### Roadmap

- [x] Multi-location (one event → multiple points)
- [x] LLM classification via Cloudflare Workers AI
- [x] Deduplication by (location, type, hour)
- [x] Settings panel on the right
- [x] Dark theme via CSS filter
- [x] Time filter chips (6h/24h/3d/7d/All)
- [ ] Auto-cleanup of old events (7+ days)
- [ ] Timelapse — view the map on a past date
- [ ] Artillery calculator (HIMARS/M777 and others)
- [ ] Export events to GeoJSON
- [ ] Enhanced popups with media previews

### License

The project code is distributed under the [MIT](LICENSE) license. The project uses open data from public sources — Telegram channels, DeepStateMap, Project Owl, NASA FIRMS, GeoNames. Terms of use for this data are defined by their original sources.

**Important:** the map is not a military planning tool and provides no accuracy guarantees. All data is an aggregation of public messages requiring independent verification.

---

## Контакты · Контакти · Contact

- GitHub Issues: для багов и предложений · для багів і пропозицій · for bugs and suggestions
- Pull Requests: приветствуются · вітаються · welcome
