
(function() {
  var indexData = null;
  var sourceNames = { deepstate: 'DeepState', project_owl: 'Project Owl' };
  var statusLabels = { changed: 'Версия изменилась', unchanged: 'Без изменений', baseline: 'Первая версия', error: 'Ошибка источника' };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function addLink(parent, label, href) {
    if (!href) return;
    var parsed;
    try {
      parsed = new URL(String(href));
    } catch (_) {
      return;
    }
    // The manifest contains upstream references, never executable or arbitrary URLs.
    if (parsed.protocol !== 'https:' ||
        ['github.com', 'raw.githubusercontent.com'].indexOf(parsed.hostname.toLowerCase()) === -1 ||
        parsed.username || parsed.password) return;
    var a = el('a', '', label);
    a.href = parsed.href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    parent.appendChild(a);
  }
  function formatSize(value) {
    var n = Number(value);
    if (!isFinite(n) || n <= 0) return '';
    return (n / 1048576).toFixed(2) + ' MiB';
  }
  function formatTime(value) {
    if (!value) return 'время не указано';
    var d = new Date(value);
    return isNaN(d.getTime()) ? String(value) : d.toLocaleString('ru-RU', {timeZone:'UTC'}) + ' UTC';
  }
  function visibleSources(day) {
    var selected = document.getElementById('sourceFilter').value;
    var entries = day.sources || {};
    return Object.keys(entries).filter(function(key) {
      return selected === 'all' || key === selected;
    }).map(function(key) { return {id:key, item:entries[key]}; });
  }
  function render() {
    if (!indexData) return;
    var root = document.getElementById('history');
    root.replaceChildren();
    var selectedDate = document.getElementById('dateFilter').value;
    var changeMode = document.getElementById('changeFilter').value;
    var days = (indexData.snapshots || []).filter(function(day) {
      if (selectedDate && day.date !== selectedDate) return false;
      var sources = visibleSources(day);
      if (!sources.length) return false;
      if (changeMode === 'changed' && !sources.some(function(s) { return s.item.change_status === 'changed'; })) return false;
      if (changeMode === 'errors' && !sources.some(function(s) {
        return s.item.status === 'error' || !!s.item.last_attempt_error;
      })) return false;
      return true;
    });
    document.getElementById('status').textContent =
      'Записей: ' + (indexData.snapshot_count || days.length) +
      ' · Создано: ' + formatTime(indexData.generated_at) +
      ' · Показано дней: ' + days.length;

    if (!days.length) {
      root.appendChild(el('div', 'empty', 'Для выбранных фильтров записей нет.'));
      return;
    }
    days.forEach(function(day) {
      var card = el('article', 'day');
      var head = el('div', 'day-head');
      head.appendChild(el('h2', '', day.date || 'Дата неизвестна'));
      head.appendChild(el('span', 'muted', 'Журнал сформирован: ' + formatTime(day.generated_at)));
      card.appendChild(head);
      var list = el('div', 'sources');
      visibleSources(day).forEach(function(source) {
        var item = source.item || {};
        var sourceCard = el('section', 'source');
        var sourceHead = el('div', 'source-head');
        sourceHead.appendChild(el('strong', '', sourceNames[source.id] || source.id));
        var state = item.status === 'error' ? 'error' : (item.change_status || 'baseline');
        sourceHead.appendChild(el('span', 'status ' + state, item.status === 'error' ? statusLabels.error : (statusLabels[state] || state)));
        sourceCard.appendChild(sourceHead);
        if (item.last_attempt_error) {
          sourceCard.appendChild(el('p', 'muted', 'Последняя попытка обновления завершилась ошибкой: ' + item.last_attempt_error));
        }
        if (item.status === 'error') {
          sourceCard.appendChild(el('p', 'muted', item.error || 'Не удалось получить версию источника.'));
        } else {
          sourceCard.appendChild(el('p', 'muted', 'Дата слоя: ' + (item.snapshot_date || 'не указана')));
          sourceCard.appendChild(el('p', 'muted', 'Коммит источника: ' + formatTime(item.upstream_commit_date)));
          if (item.archive_size_bytes) sourceCard.appendChild(el('p', 'muted', 'Размер архива: ' + formatSize(item.archive_size_bytes)));
          if (item.revision) sourceCard.appendChild(el('p', 'muted', 'Версия: ' + item.revision));
          var links = el('div', 'links');
          addLink(links, item.source_path && item.source_path.endsWith('.kmz') ? 'Открыть KMZ' : 'Открыть GeoJSON.GZ', item.source_url);
          addLink(links, 'Коммит источника', item.upstream_commit_url);
          sourceCard.appendChild(links);
        }
        list.appendChild(sourceCard);
      });
      card.appendChild(list);
      root.appendChild(card);
    });
  }

  fetch('./data/territory-history/index.json', {cache:'no-store'})
    .then(function(response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    })
    .then(function(payload) {
      if (!payload || !Array.isArray(payload.snapshots)) throw new Error('Некорректный индекс истории');
      indexData = payload;
      render();
    })
    .catch(function(error) {
      document.getElementById('status').textContent = 'Не удалось загрузить историю: ' + error.message;
      document.getElementById('history').appendChild(el('div','empty','Проверьте доступность файла data/territory-history/index.json.'));
    });

  ['sourceFilter','changeFilter','dateFilter'].forEach(function(id) {
    document.getElementById(id).addEventListener('change', render);
  });
})();
