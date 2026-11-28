
    window.addEventListener('error', function(e) {
      var box = document.getElementById('errorBox');
      if (box) { box.style.display = 'block'; box.textContent = 'Ошибка: ' + e.message; }
    });
    function isMobile() { return window.innerWidth <= 768; }

    function escapeHtml(value) {
      return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // External links/media are restricted to HTTPS; never allow javascript: or data: URLs.
    function safeHttpUrl(value) {
      if (value == null || String(value).trim() === '') return '';
      try {
        var parsed = new URL(String(value).trim(), window.location.href);
        return parsed.protocol === 'https:' ? parsed.href : '';
      } catch (e) {
        return '';
      }
    }

    function isDirectVideoFile(value) {
      try {
        var parsed = new URL(value);
        return /\.(mp4|m4v|webm|ogv|ogg)$/i.test(parsed.pathname);
      } catch (e) { return false; }
    }

    function telegramEmbedUrl(value) {
      try {
        var parsed = new URL(value);
        if (parsed.protocol !== 'https:' || !/^(t\.me|telegram\.me)$/i.test(parsed.hostname)) return '';
        var match = parsed.pathname.match(/^\/(?:s\/)?([A-Za-z0-9_]{3,})\/(\d+)\/?$/);
        if (!match) return '';
        return 'https://t.me/' + match[1] + '/' + match[2] + '?embed=1';
      } catch (e) { return ''; }
    }
  