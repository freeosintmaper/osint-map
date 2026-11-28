
(function initZoneAIAssistant() {
  var overlay = document.getElementById('zoneAIOverlay');
  var textarea = document.getElementById('zoneAIInstruction');
  var statusEl = document.getElementById('zoneAIStatus');
  var resultsEl = document.getElementById('zoneAIResults');
  var generateBtn = document.getElementById('btnZoneAIGenerate');
  var autoBtn = document.getElementById('btnZoneAIAuto');
  var previewLayers = [];
  var proposals = [];
  var requestZoneSnapshot = [];
  var busy = false;

  function setStatus(message, kind) {
    statusEl.textContent = message || '';
    statusEl.className = kind || '';
  }
  function clearPreview() {
    previewLayers.forEach(function(layer) { try { map.removeLayer(layer); } catch (e) {} });
    previewLayers = [];
  }
  function closeAssistant() {
    overlay.classList.remove('open');
    clearPreview();
  }
  function openAssistant() {
    if (!sb) {
      alert('Нет подключения к Supabase.');
      return;
    }
    overlay.classList.add('open');
    setStatus('', '');
    resultsEl.replaceChildren();
    clearPreview();
    proposals = [];
    textarea.focus();
  }
  function compactGeometry(geometry) {
    if (!geometry || geometry.type !== 'Polygon' || !Array.isArray(geometry.coordinates) || !geometry.coordinates.length) return null;
    var ring = geometry.coordinates[0];
    if (!Array.isArray(ring) || ring.length < 4) return null;
    var points = ring;
    if (ring.length > 40) {
      var step = Math.ceil((ring.length - 1) / 39);
      points = [];
      for (var i = 0; i < ring.length - 1; i += step) points.push(ring[i]);
      points.push(points[0]);
    }
    return { type: 'Polygon', coordinates: [points] };
  }
  function gatherZones() {
    var features = userZonesLayer && userZonesLayer.toGeoJSON ? userZonesLayer.toGeoJSON().features || [] : [];
    return features.slice(0, 50).map(function(feature) {
      var props = feature.properties || {};
      return {
        id: props.id == null ? null : props.id,
        category: ['russia', 'ukraine', 'grey'].indexOf(props.category) >= 0 ? props.category : 'russia',
        geometry: compactGeometry(feature.geometry)
      };
    }).filter(function(zone) { return !!zone.geometry; });
  }
  function gatherRecentEvents() {
    var events = window.TG_DATA && Array.isArray(window.TG_DATA.events) ? window.TG_DATA.events : [];
    var cutoff = Date.now() - 48 * 60 * 60 * 1000;
    return events.filter(function(event) {
      var time = Date.parse(event.date || '');
      return isFinite(time) && time >= cutoff && isFinite(Number(event.lat)) && isFinite(Number(event.lng));
    }).sort(function(a, b) { return Date.parse(b.date) - Date.parse(a.date); }).slice(0, 25).map(function(event) {
      return {
        id: event.id == null ? null : event.id,
        date: String(event.date || '').slice(0, 40),
        type: String(event.event_type || '').slice(0, 80),
        location: String(event.location || '').slice(0, 100),
        country: String(event.country || '').slice(0, 10),
        lat: Number(event.lat),
        lng: Number(event.lng),
        description: String(event.description || '').slice(0, 260),
        url: safeHttpUrl(event.url)
      };
    });
  }
  function validProposal(proposal) {
    if (!proposal || ['add', 'update'].indexOf(proposal.action) < 0) return false;
    if (['russia', 'ukraine', 'grey'].indexOf(proposal.category) < 0) return false;
    var proposalZones = requestZoneSnapshot.length ? requestZoneSnapshot : gatherZones();
    if (proposal.action === 'update' && (proposal.zoneId == null || !proposalZones.some(function(zone) { return String(zone.id) === String(proposal.zoneId); }))) return false;
    if (proposal.action === 'add' && proposal.zoneId != null) return false;
    var geometry = proposal.geometry;
    if (!geometry || geometry.type !== 'Polygon' || !Array.isArray(geometry.coordinates) || geometry.coordinates.length !== 1) return false;
    var ring = geometry.coordinates[0];
    if (!Array.isArray(ring) || ring.length < 4 || ring.length > 501) return false;
    var first = ring[0], last = ring[ring.length - 1];
    if (!Array.isArray(first) || !Array.isArray(last) || first.length < 2 || last.length < 2 || first[0] !== last[0] || first[1] !== last[1]) return false;
    return ring.every(function(point) {
      return Array.isArray(point) && point.length >= 2 &&
        Number.isFinite(point[0]) && Number.isFinite(point[1]) &&
        point[0] >= -180 && point[0] <= 180 && point[1] >= -90 && point[1] <= 90;
    });
  }
  function categoryColor(category) {
    if (category === 'ukraine') return '#0055cc';
    if (category === 'grey') return '#666666';
    return '#cc0000';
  }
  function showProposals(data) {
    clearPreview();
    resultsEl.replaceChildren();
    proposals = (Array.isArray(data.proposals) ? data.proposals : []).filter(validProposal);
    var explanation = [data.summary, data.question].filter(function(value) { return typeof value === 'string' && value.trim(); }).join('\n\n');
    if (explanation) setStatus(explanation, '');
    if (!proposals.length) {
      if (!explanation) setStatus('ИИ не вернул подходящих предложений. Попробуй уточнить команду или координаты.', '');
      return;
    }
    proposals.forEach(function(proposal, index) {
      var layer = L.geoJSON({ type: 'Feature', properties: { category: proposal.category }, geometry: proposal.geometry }, {
        interactive: false,
        style: function(feature) {
          var color = categoryColor((feature.properties || {}).category);
          return { color: color, weight: 3, opacity: 1, fillColor: color, fillOpacity: 0.08, dashArray: '6,5' };
        }
      });
      layer.addTo(map);
      previewLayers.push(layer);

      var card = document.createElement('section');
      card.className = 'zone-ai-proposal';
      var title = document.createElement('h4');
      title.textContent = String(proposal.name || (proposal.action === 'update' ? 'Предложение изменить зону' : 'Новая зона'));
      card.appendChild(title);
      var meta = document.createElement('div');
      meta.className = 'zone-ai-meta';
      var confidence = Number(proposal.confidence);
      meta.textContent = (proposal.action === 'update' ? 'Изменение существующей зоны #' + String(proposal.zoneId) : 'Новая зона') +
        ' · категория: ' + proposal.category + (Number.isFinite(confidence) ? ' · уверенность ИИ: ' + Math.round(Math.max(0, Math.min(1, confidence)) * 100) + '%' : '');
      card.appendChild(meta);
      var reason = document.createElement('p');
      reason.textContent = String(proposal.reason || 'Обоснование не предоставлено.');
      card.appendChild(reason);
      if (Array.isArray(proposal.sourceEventIds) && proposal.sourceEventIds.length) {
        var refs = document.createElement('p');
        refs.textContent = 'Связанные события: ' + proposal.sourceEventIds.slice(0, 10).map(String).join(', ');
        card.appendChild(refs);
      }
      var actions = document.createElement('div');
      actions.className = 'zone-ai-proposal-actions';
      var showBtn = document.createElement('button');
      showBtn.type = 'button';
      showBtn.textContent = 'Показать на карте';
      showBtn.addEventListener('click', function() {
        var bounds = layer.getBounds();
        if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
      });
      actions.appendChild(showBtn);
      var applyBtn = document.createElement('button');
      applyBtn.type = 'button';
      applyBtn.className = 'primary';
      applyBtn.textContent = 'Применить предложение';
      applyBtn.addEventListener('click', function() { applyProposal(proposal, applyBtn, index); });
      actions.appendChild(applyBtn);
      card.appendChild(actions);
      resultsEl.appendChild(card);
    });
    if (!proposals.length) setStatus('Предложения пришли, но не прошли проверку геометрии. Ничего не изменено.', 'error');
  }
  function applyProposal(proposal, button, proposalIndex) {
    if (busy || !sb) return;
    if (!validProposal(proposal)) {
      setStatus('Предложение изменилось или геометрия некорректна. Сгенерируй его заново.', 'error');
      return;
    }
    if (proposal.action === 'update') {
      var currentZone = gatherZones().find(function(zone) { return String(zone.id) === String(proposal.zoneId); });
      var baseZone = requestZoneSnapshot.find(function(zone) { return String(zone.id) === String(proposal.zoneId); });
      if (!currentZone || !baseZone || currentZone.category !== baseZone.category ||
          JSON.stringify(currentZone.geometry) !== JSON.stringify(baseZone.geometry)) {
        setStatus('Эта зона изменилась после получения предложения. Сгенерируй предложение заново, чтобы не затереть новые изменения.', 'error');
        return;
      }
    }
    var auth = sb.auth.getSession();
    auth.then(function(sessionResult) {
      if (sessionResult.error || !sessionResult.data || !sessionResult.data.session) {
        setStatus('Сессия истекла. Войди в админ-панель заново.', 'error');
        return;
      }
      busy = true;
      button.disabled = true;
      button.textContent = 'Сохраняем…';
      var request;
      if (proposal.action === 'add') {
        request = sb.from('control_zones').insert({ category: proposal.category, geometry: proposal.geometry });
      } else {
        request = sb.from('control_zones').update({ category: proposal.category, geometry: proposal.geometry }).eq('id', proposal.zoneId);
      }
      request.then(function(result) {
        busy = false;
        if (result.error) {
          button.disabled = false;
          button.textContent = 'Повторить применение';
          setStatus('Не удалось сохранить: ' + result.error.message, 'error');
          return;
        }
        button.textContent = '✓ Применено';
        button.disabled = true;
        button.className = '';
        setStatus('Предложение сохранено. Проверь обновлённую зону на карте.', 'success');
        if (previewLayers[proposalIndex]) {
          try { map.removeLayer(previewLayers[proposalIndex]); } catch (e) {}
          previewLayers[proposalIndex] = null;
        }
        if (typeof loadUserZones === 'function') loadUserZones();
      }).catch(function(error) {
        busy = false;
        button.disabled = false;
        button.textContent = 'Повторить применение';
        setStatus('Ошибка сохранения: ' + String(error && error.message || error), 'error');
      });
    }).catch(function(error) {
      setStatus('Не удалось проверить сессию: ' + String(error && error.message || error), 'error');
    });
  }
  function requestProposals(mode) {
    if (busy) return;
    var instruction = textarea.value.trim();
    if (mode === 'command' && !instruction) {
      setStatus('Сначала напиши, что именно изменить. Укажи координаты, если зона должна быть привязана к конкретному месту.', 'error');
      textarea.focus();
      return;
    }
    if (!sb) {
      setStatus('Нет соединения с Supabase.', 'error');
      return;
    }
    busy = true;
    generateBtn.disabled = true;
    autoBtn.disabled = true;
    setStatus('ИИ анализирует запрос и готовит черновик…', '');
    resultsEl.replaceChildren();
    clearPreview();
    sb.auth.getSession().then(function(sessionResult) {
      var session = sessionResult.data && sessionResult.data.session;
      if (sessionResult.error || !session) throw new Error('Нужен вход в админ-панель.');
      var center = map.getCenter();
      requestZoneSnapshot = gatherZones();
      var payload = {
        mode: mode,
        instruction: instruction,
        zones: requestZoneSnapshot,
        events: mode === 'auto' ? gatherRecentEvents() : [],
        mapCenter: { lat: center.lat, lng: center.lng, zoom: map.getZoom() }
      };
      return fetch(SB_URL + '/functions/v1/zone-assistant', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SB_KEY,
          'Authorization': 'Bearer ' + session.access_token
        },
        body: JSON.stringify(payload)
      });
    }).then(function(response) {
      return response.json().catch(function() { return {}; }).then(function(body) {
        if (!response.ok) {
          var message = body.error || ('HTTP ' + response.status);
          if (response.status === 404 || response.status === 503) {
            message += ' — функцию ИИ ещё нужно развернуть и настроить. См. docs/zone-ai-setup.md в репозитории.';
          }
          throw new Error(message);
        }
        return body;
      });
    }).then(function(data) {
      showProposals(data);
    }).catch(function(error) {
      setStatus(String(error && error.message || error), 'error');
    }).finally(function() {
      busy = false;
      generateBtn.disabled = false;
      autoBtn.disabled = false;
    });
  }

  document.getElementById('btnOpenZoneAI').addEventListener('click', openAssistant);
  document.getElementById('btnZoneAIClose').addEventListener('click', closeAssistant);
  overlay.addEventListener('click', function(event) { if (event.target === overlay) closeAssistant(); });
  document.getElementById('btnZoneAIGenerate').addEventListener('click', function() { requestProposals('command'); });
  document.getElementById('btnZoneAIAuto').addEventListener('click', function() { requestProposals('auto'); });
  document.addEventListener('keydown', function(event) { if (event.key === 'Escape') closeAssistant(); });
})();
