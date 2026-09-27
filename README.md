# OSINT Map

**🌐 Language / Мова / Язык:** [English](#english) · [Українська](#українська) · [Русский](#русский)

**Live site:** https://freeosintmaper.github.io/osint-map/

---

## English

### About
Interactive map aggregating open-source data about events in Ukraine and Russia.

### What it shows
- **Telegram events** — strikes, air raid alerts, military operations, incidents. Parsed from public Telegram channels every 15 minutes.
- **Control zones (DeepStateMap)** — territory held by RF, per the Ukrainian OSINT project DeepStateMap.
- **Project Owl layers** — independent OSINT project (Ukraine Control Map). Four categories:
  - 🔴 Russian actions — offensives, axes, incursions
  - 🔵 Ukrainian actions — counterattacks
  - 🟣 Holding areas — concentration zones
  - ⚫ Grey zone
- **User zones** — manually added polygons (stored via Supabase).

### Data sources
**Telegram channels:**
- Ukrainian: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Russian: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Map layers:**
- [DeepStateMap](https://deepstatemap.live) — RF-controlled territory (Ukrainian OSINT project)
- [Project Owl / Ukraine Control Map](https://github.com/owlmaps/UAControlMapBackups) — independent OSINT data, historical military activity

### Features
- 🗺️ Interactive Leaflet map
- 📍 Event clustering
- 🎨 SVG icons by event type
- 🌙 Dark and light themes
- 🌐 Three languages: Russian, Ukrainian, English
- 📱 Mobile version with toggle buttons
- ✏️ Drawing tools: markers, lines, arrows, polygons, rectangles, circles, distance measurement
- 🔐 Admin login for editing control zones

### Neutrality
This map **aggregates** open data from multiple sources and **does not perform its own analysis**.
- Every event links to its original source.
- Events come from both Ukrainian and Russian sources.
- Frontline data is approximate and may differ from the real situation.
- Project Owl is an independent OSINT project — its data may lag.

**Goal:** show different perspectives so users can compare them and draw their own conclusions.

### Tech stack
- Pure HTML/JS (no build)
- Leaflet, Leaflet.draw, Leaflet.markercluster, Leaflet.polylineDecorator
- JSZip + togeojson (for Project Owl KMZ parsing)
- Supabase (auth + storage of user zones)
- GitHub Actions (automated updates)
- GitHub Pages (hosting)

### Disclaimer
This project is created for **educational and research purposes**. All data is public, from open sources. No warranty is provided for its accuracy or completeness.

---

## Українська

### Про проект
Інтерактивна карта, що агрегує відкриті дані про події в Україні та Росії.

### Що показує карта
- **Події з Telegram** — удари, повітряні тривоги, бойові дії, інциденти. Дані парсяться з публічних Telegram-каналів кожні 15 хвилин.
- **Зони контролю (DeepStateMap)** — територія, яку займає РФ, за даними українського OSINT-проекту DeepStateMap.
- **Шари Project Owl** — незалежний OSINT-проект (Ukraine Control Map). Чотири категорії:
  - 🔴 Дії РФ — наступи, осі, вторгнення
  - 🔵 Дії ЗСУ — контрнаступи
  - 🟣 Місця зосередження — зони концентрації військ
  - ⚫ Сіра зона
- **Мої зони** — полігони, додані вручну (зберігаються через Supabase).

### Джерела даних
**Telegram-канали:**
- Українські: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Російські: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографічні шари:**
- [DeepStateMap](https://deepstatemap.live) — території, які займає РФ
- [Project Owl / Ukraine Control Map](https://github.com/owlmaps/UAControlMapBackups) — незалежні OSINT-дані

### Можливості
- 🗺️ Інтерактивна карта на Leaflet
- 📍 Кластеризація подій
- 🎨 SVG-іконки за типами подій
- 🌙 Темна та світла теми
- 🌐 Три мови: російська, українська, англійська
- 📱 Мобільна версія
- ✏️ Інструменти малювання
- 🔐 Вхід для адміна

### Нейтральність
Карта **агрегує** відкриті дані і **не проводить власний аналіз**.
- Кожна подія має посилання на першоджерело.
- Події надходять від українських і російських джерел.
- Лінія фронту — приблизна.

### Технічна інформація
- Чистий HTML/JS (без збірки)
- Leaflet, Leaflet.draw, Leaflet.markercluster
- JSZip + togeojson
- Supabase
- GitHub Actions, GitHub Pages

### Дисклеймер
Проект створено в **освітніх та дослідницьких цілях**. Всі дані — публічні. Автор не несе відповідальності за їх точність.

---

## Русский

### О проекте
Интерактивная карта, агрегирующая открытые данные о событиях в Украине и России.

### Что показывает карта
- **События из Telegram** — удары, воздушные тревоги, боевые действия, инциденты. Данные парсятся из публичных Telegram-каналов каждые 15 минут.
- **Зоны контроля (DeepStateMap)** — территория, занимаемая РФ, по данным украинского OSINT-проекта DeepStateMap.
- **Слои Project Owl** — независимый OSINT-проект (Ukraine Control Map). Четыре категории:
  - 🔴 Действия РФ — наступления, оси, вторжения
  - 🔵 Действия ВСУ — контрнаступления
  - 🟣 Места сосредоточения — зоны концентрации войск
  - ⚫ Серая зона
- **Мои зоны** — полигоны, добавленные вручную (хранятся через Supabase).

### Источники данных
**Telegram-каналы:**
- Украинские: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Российские: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографические слои:**
- [DeepStateMap](https://deepstatemap.live) — территории, занимаемые РФ
- [Project Owl / Ukraine Control Map](https://github.com/owlmaps/UAControlMapBackups) — независимые OSINT-данные

### Возможности
- 🗺️ Интерактивная карта на Leaflet
- 📍 Кластеризация событий
- 🎨 SVG-иконки по типам событий
- 🌙 Тёмная и светлая темы
- 🌐 Три языка
- 📱 Мобильная версия
- ✏️ Инструменты рисования
- 🔐 Вход для админа

### Нейтральность
Карта **агрегирует** открытые данные и **не проводит собственный анализ**.
- Каждое событие имеет ссылку на первоисточник.
- События приходят от украинских и российских источников.
- Линия фронта — приблизительная.

### Техническая информация
- Чистый HTML/JS (без сборки)
- Leaflet, Leaflet.draw, Leaflet.markercluster
- JSZip + togeojson
- Supabase
- GitHub Actions, GitHub Pages

### Дисклеймер
Проект создан в **образовательных и исследовательских целях**. Все данные — публичные. Автор не несёт ответственности за их точность.
