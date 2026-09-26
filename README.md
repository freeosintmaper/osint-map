# OSINT Map

**🌐 Language / Мова / Язык:** [English](#english) · [Українська](#українська) · [Русский](#русский)

**Live site:** https://freeosintmaper.github.io/osint-map/

---

## English

### About
Interactive map visualizing open-source data about events in Ukraine and Russia.

### What it shows
- **Telegram events** — strikes, air raid alerts, military operations, incidents. Parsed from public Telegram channels every 15 minutes.
- **Control zones** — territory held by RF (based on DeepStateMap).
- **Ukrainian counteroffensives** — historical layer (based on ISW).

### Data sources
**Telegram channels:**
- Ukrainian: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Russian: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Map layers:**
- DeepStateMap — RF-controlled territory
- ISW (Institute for the Study of War) — Ukrainian counteroffensives

### Features
- 🗺️ Interactive Leaflet map
- 📍 Event clustering
- 🎨 SVG icons by event type
- 🌙 Dark and light themes
- 🌐 Three languages: Russian, Ukrainian, English
- ✏️ Drawing tools: markers, lines, arrows, polygons, circles, distance measurement

### Neutrality
The map **aggregates** open data from multiple sources and **does not perform its own analysis**.
- Every event links to its original source (Telegram channel).
- Events come from both Ukrainian and Russian sources.
- The frontline is approximate and may differ from the real situation.

**Goal:** show different perspectives so users can compare them and draw their own conclusions.

### Tech stack
- Pure HTML/JS (no build)
- Leaflet, Leaflet.draw, Leaflet.markercluster
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
- **Зони контролю** — територія, яку займає РФ (за даними DeepStateMap).
- **Контрнаступи ЗСУ** — історичний шар (за даними ISW).

### Джерела даних
**Telegram-канали:**
- Українські: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Російські: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографічні шари:**
- DeepStateMap — території, які займає РФ
- ISW (Institute for the Study of War) — контрнаступи ЗСУ

### Можливості
- 🗺️ Інтерактивна карта на Leaflet
- 📍 Кластеризація подій
- 🎨 SVG-іконки за типами подій
- 🌙 Темна та світла теми
- 🌐 Три мови: російська, українська, англійська
- ✏️ Інструменти малювання: мітки, лінії, стрілки, зони, коло, вимірювання відстані

### Нейтральність
Карта **агрегує** відкриті дані з різних джерел і **не проводить власний аналіз**.
- Кожна подія має посилання на першоджерело (Telegram-канал).
- Події надходять як від українських, так і від російських джерел.
- Лінія фронту — приблизна і може відрізнятися від реальної обстановки.

**Мета проекту** — показати різні погляди, щоб користувач міг порівняти їх і зробити власні висновки.

### Технічна інформація
- Чистий HTML/JS (без збірки)
- Leaflet, Leaflet.draw, Leaflet.markercluster
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
- **Зоны контроля** — территория, занимаемая РФ (по данным DeepStateMap).
- **Контрнаступления ВСУ** — исторический слой (по данным ISW).

### Источники данных
**Telegram-каналы:**
- Украинские: `ukrpravda_news`, `operativnoZSU`, `amk_mapping`, `uniannet`
- Российские: `rybar`, `militarysummary`, `readovkanews`, `tass_agency`
- OSINT: `UAWeapons`, `Osinttechnical`

**Картографические слои:**
- DeepStateMap — территории, занимаемые РФ
- ISW (Institute for the Study of War) — контрнаступления ВСУ

### Возможности
- 🗺️ Интерактивная карта на Leaflet
- 📍 Кластеризация событий
- 🎨 SVG-иконки по типам событий
- 🌙 Тёмная и светлая темы
- 🌐 Три языка: русский, украинский, английский
- ✏️ Инструменты рисования: метки, линии, стрелки, зоны, круг, измерение расстояния

### Нейтральность
Карта **агрегирует** открытые данные из разных источников и **не проводит собственный анализ**.
- Каждое событие имеет ссылку на первоисточник (Telegram-канал).
- События приходят как от украинских, так и от российских источников.
- Линия фронта — приблизительная и может отличаться от реальной обстановки.

**Цель проекта** — показать разные взгляды, чтобы пользователь мог сравнить их и сделать собственные выводы.

### Техническая информация
- Чистый HTML/JS (без сборки)
- Leaflet, Leaflet.draw, Leaflet.markercluster
- Python (парсер Telegram)
- GitHub Actions (автоматическое обновление)
- GitHub Pages (хостинг)

### Поддержка
Если проект полезен — можете поддержать его развитие:
**[Донат через DonationAlerts](https://www.donationalerts.com/r/freeosintmapper)**

### Дисклеймер
Проект создан в **образовательных и исследовательских целях**. Все данные — публичные, из открытых источников. Автор не несёт ответственности за их точность.
