# OSINT Map

**🌐 Language / Мова / Язык:** [English](#english) · [Українська](#українська) · [Русский](#русский)

**Live site:** https://freeosintmaper.github.io/osint-map/

---

## English

### About
Interactive map visualizing open-source data about events in Ukraine and Russia.

### What it shows
- **Telegram events** — strikes, air raid alerts, military operations, incidents. Parsed from public Telegram channels every 15 minutes.
- **Control zones (DeepStateMap)** — territory held by RF, per the Ukrainian OSINT project DeepStateMap.
- **Project Owl layers** — independent OSINT project (Ukraine Control Map). Four categories:
  - 🔴 Russian actions — offensives, axes, incursions
  - 🔵 Ukrainian actions — counterattacks
  - 🟣 Holding areas — concentration zones
  - ⚫ Grey zone
- **User zones** — admin-drawn polygons (controlled via Supabase).

### Data sources
**Telegram channels:**
- Ukrainian: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Russian: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Map layers:**
- DeepStateMap — RF-controlled territory
- Project Owl (Ukraine Control Map) — historical military activity, positions, control zones
- User zones — manually added via the admin panel

### Features
- 🗺️ Interactive Leaflet map
- 📍 Event clustering
- 🎨 SVG icons by event type
- 🌙 Dark and light themes
- 🌐 Three languages: Russian, Ukrainian, English
- 📱 Mobile version with toggle buttons
- ✏️ Drawing tools: markers, lines, arrows, polygons, rectangles, circles, distance measurement
- 🔐 Admin login for editing control zones (Supabase)
- 🔗 Each event links to its original source

### Neutrality
The map **aggregates** open data from multiple sources and **does not perform its own analysis**.
- Every event links to its original source (Telegram channel).
- Events come from both Ukrainian and Russian sources.
- The frontline is approximate and may differ from the real situation.
- Project Owl is an independent OSINT project — the data may lag and may not reflect the current front line.

**Goal:** show different perspectives so users can compare them and draw their own conclusions.

### Tech stack
- Pure HTML/JS (no build)
- Leaflet, Leaflet.draw, Leaflet.markercluster, Leaflet.polylineDecorator
- JSZip + togeojson (for Project Owl KMZ parsing)
- Supabase (auth + storage of user zones)
- Python (Telegram parser)
- GitHub Actions (automated updates)
- GitHub Pages (hosting)

### Support
If you find this project useful, you can support its development:
**[Donate via DonationAlerts](https://www.donationalerts.com/r/freeosintmapper)**

### Disclaimer
The project is created for **educational and research purposes**. All data is public, from open sources. The author is not responsible for its accuracy or consequences of use.

---

## Українська

### Про проект
Інтерактивна карта для візуалізації відкритих даних про події в Україні та Росії.

### Що показує карта
- **Події з Telegram** — удари, повітряні тривоги, бойові дії, інциденти. Дані парсяться з публічних Telegram-каналів кожні 15 хвилин.
- **Зони контролю (DeepStateMap)** — територія, яку займає РФ, за даними українського OSINT-проекту DeepStateMap.
- **Шари Project Owl** — незалежний OSINT-проект (Ukraine Control Map). Чотири категорії:
  - 🔴 Дії РФ — наступи, осі, вторгнення
  - 🔵 Дії ЗСУ — контрнаступи
  - 🟣 Місця зосередження — зони концентрації військ
  - ⚫ Сіра зона
- **Мої зони** — полігони, намальовані адміном (керується через Supabase).

### Джерела даних
**Telegram-канали:**
- Українські: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Російські: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографічні шари:**
- DeepStateMap — території, які займає РФ
- Project Owl (Ukraine Control Map) — історична воєнна активність, позиції, зони контролю
- Мої зони — додані вручну через адмін-панель

### Можливості
- 🗺️ Інтерактивна карта на Leaflet
- 📍 Кластеризація подій
- 🎨 SVG-іконки за типами подій
- 🌙 Темна та світла теми
- 🌐 Три мови: російська, українська, англійська
- 📱 Мобільна версія з кнопками навігації
- ✏️ Інструменти малювання: мітки, лінії, стрілки, зони, прямокутники, кола, вимірювання відстані
- 🔐 Вхід для адміна та редагування зон контролю (Supabase)
- 🔗 Кожна подія має посилання на першоджерело

### Нейтральність
Карта **агрегує** відкриті дані з різних джерел і **не проводить власний аналіз**.
- Кожна подія має посилання на першоджерело (Telegram-канал).
- Події надходять як від українських, так і від російських джерел.
- Лінія фронту — приблизна і може відрізнятися від реальної обстановки.
- Project Owl — незалежний OSINT-проект, дані можуть відставати і не відображати поточну лінію фронту.

**Мета проекту** — показати різні погляди, щоб користувач міг порівняти їх і зробити власні висновки.

### Технічна інформація
- Чистий HTML/JS (без збірки)
- Leaflet, Leaflet.draw, Leaflet.markercluster, Leaflet.polylineDecorator
- JSZip + togeojson (для парсингу KMZ Project Owl)
- Supabase (авторизація + зберігання зон користувача)
- Python (парсер Telegram)
- GitHub Actions (автоматичне оновлення)
- GitHub Pages (хостинг)

### Підтримка
Якщо проект корисний — можете підтримати його розвиток:
**[Донат через DonationAlerts](https://www.donationalerts.com/r/freeosintmapper)**

### Дисклеймер
Проект створено в **освітніх та дослідницьких цілях**. Всі дані — публічні, з відкритих джерел. Автор не несе відповідальності за їх точність.

---

## Русский

### О проекте
Интерактивная карта для визуализации открытых данных о событиях в Украине и России.

### Что показывает карта
- **События из Telegram** — удары, воздушные тревоги, боевые действия, инциденты. Данные парсятся из публичных Telegram-каналов каждые 15 минут.
- **Зоны контроля (DeepStateMap)** — территория, занимаемая РФ, по данным украинского OSINT-проекта DeepStateMap.
- **Слои Project Owl** — независимый OSINT-проект (Ukraine Control Map). Четыре категории:
  - 🔴 Действия РФ — наступления, оси, вторжения
  - 🔵 Действия ВСУ — контрнаступления
  - 🟣 Места сосредоточения — зоны концентрации войск
  - ⚫ Серая зона
- **Мои зоны** — полигоны, нарисованные админом (управляются через Supabase).

### Источники данных
**Telegram-каналы:**
- Украинские: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Российские: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографические слои:**
- DeepStateMap — территории, занимаемые РФ
- Project Owl (Ukraine Control Map) — историческая военная активность, позиции, зоны контроля
- Мои зоны — добавленные вручную через админ-панель

### Возможности
- 🗺️ Интерактивная карта на Leaflet
- 📍 Кластеризация событий
- 🎨 SVG-иконки по типам событий
- 🌙 Тёмная и светлая темы
- 🌐 Три языка: русский, украинский, английский
- 📱 Мобильная версия с кнопками навигации
- ✏️ Инструменты рисования: метки, линии, стрелки, зоны, прямоугольники, круги, измерение расстояния
- 🔐 Вход для админа и редактирование зон контроля (Supabase)
- 🔗 Каждое событие имеет ссылку на первоисточник

### Нейтральность
Карта **агрегирует** открытые данные из разных источников и **не проводит собственный анализ**.
- Каждое событие имеет ссылку на первоисточник (Telegram-канал).
- События приходят как от украинских, так и от российских источников.
- Линия фронта — приблизительная и может отличаться от реальной обстановки.
- Project Owl — независимый OSINT-проект, данные могут отставать и не отражать текущую линию фронта.

**Цель проекта** — показать разные взгляды, чтобы пользователь мог сравнить их и сделать собственные выводы.

### Техническая информация
- Чистый HTML/JS (без сборки)
- Leaflet, Leaflet.draw, Leaflet.markercluster, Leaflet.polylineDecorator
- JSZip + togeojson (для парсинга KMZ Project Owl)
- Supabase (авторизация + хранение зон пользователя)
- Python (парсер Telegram)
- GitHub Actions (автоматическое обновление)
- GitHub Pages (хостинг)

### Поддержка
Если проект полезен — можете поддержать его развитие:
**[Донат через DonationAlerts](https://www.donationalerts.com/r/freeosintmapper)**

### Дисклеймер
Проект создан в **образовательных и исследовательских целях**. Все данные — публичные, из открытых источников. Автор не несёт ответственности за их точность.
