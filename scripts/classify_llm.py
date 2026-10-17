"""
LLM-классификация постов через Cloudflare Workers AI.
Модель: llama-3.1-8b-instruct (OpenAI-совместимый API).

Использование:
    from classify_llm import LLMClassifier
    clf = LLMClassifier()
    result = clf.classify(post_text)
    # result = {
    #     "is_event": True/False,
    #     "event_type": "Military Strike" | ... | None,
    #     "locations": [{"name": "Винница", "confidence": 0.95}, ...]
    # } или None (если LLM недоступен / ошибка)
"""
import json
import os
import re
import time
import hashlib
import sys

try:
    from openai import OpenAI
except ImportError:
    print("⚠️ openai не установлен — pip install openai", file=sys.stderr)
    OpenAI = None


CACHE_FILE = "data/llm_cache.json"
CACHE_MAX = 5000
ALLOWED_TYPES = {
    "Air Raid Alert",
    "Military Strike",
    "Military Offensive",
    "Military Operation",
    "Political Development",
}
MAX_LOCATIONS = 5
LLM_MODEL = "@cf/meta/llama-3.1-8b-instruct"


SYSTEM_PROMPT = """Ты — OSINT-аналитик. Анализируешь посты из Telegram-каналов о войне в Украине.
Отвечай ТОЛЬКО валидным JSON, без markdown, без пояснений.

Формат:
{
  "is_event": true|false,
  "event_type": "Air Raid Alert"|"Military Strike"|"Military Offensive"|"Military Operation"|"Political Development"|null,
  "locations": [{"name": "название города", "confidence": 0.0-1.0}, ...]
}

Правила:
- is_event=true ТОЛЬКО если в тексте описано конкретное военное/политическое событие, произошедшее сейчас или недавно.
- is_event=false для: аналитики, мнений, исторических справок (2010-2021), рекламы, анонсов фильмов, постов про другие страны (Йемен, Мали, Сирия, Индонезия, Африка), шуток, рассуждений.
- event_type — строго из списка выше.
- locations — ТОЛЬКО реальные города/НП, где произошло событие. НЕ включай:
  * слова-омонимы (Житель, Лесной, Мирный, Сторона, Долины, Украинское, Городской — это НЕ города в данном контексте)
  * названия областей (Брянская, Черниговская) — используй город-центр области (Брянск, Чернигов)
  * страны, регионы, направления фронта
  * места, где живёт/служит автор поста
- Если локаций нет — пустой массив.
- Если событие охватывает несколько городов — перечисли все.
- confidence — насколько уверен, что это локация события (0.0-1.0)."""


def _text_hash(text):
    return hashlib.md5(text[:500].encode("utf-8", errors="ignore")).hexdigest()


class LLMClassifier:
    def __init__(self):
        self.client = None
        self.cache = {}
        self.new_calls = 0
        self.errors = 0
        self._load_cache()
        self._init_client()

    def _init_client(self):
        if OpenAI is None:
            return
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        if not account_id or not api_token:
            print("⚠️ LLM: CLOUDFLARE_ACCOUNT_ID или CLOUDFLARE_API_TOKEN не заданы",
                  file=sys.stderr)
            return
        try:
            self.client = OpenAI(
                base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
                api_key=api_token,
            )
            print(f"🤖 LLM подключён (Cloudflare Workers AI, модель {LLM_MODEL})")
        except Exception as e:
            print(f"⚠️ LLM init: {e}", file=sys.stderr)
            self.client = None

    def _load_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"  💾 LLM-кэш: {len(self.cache)} записей")
        except Exception as e:
            print(f"  ⚠️ LLM-кэш не загрузился: {e}", file=sys.stderr)
            self.cache = {}

    def save_cache(self):
        try:
            os.makedirs("data", exist_ok=True)
            if len(self.cache) > CACHE_MAX:
                items = list(self.cache.items())[-CACHE_MAX:]
                self.cache = dict(items)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
            print(f"  💾 LLM-кэш сохранён: {len(self.cache)} записей")
        except Exception as e:
            print(f"  ⚠️ LLM-кэш не сохранился: {e}", file=sys.stderr)

    def classify(self, text):
        """Возвращает dict с результатом или None при ошибке/отсутствии LLM."""
        if self.client is None:
            return None

        h = _text_hash(text)
        if h in self.cache:
            return self.cache[h]

        try:
            resp = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text[:1500]},
                ],
                temperature=0,
                max_tokens=400,
            )
            self.new_calls += 1
            content = (resp.choices[0].message.content or "").strip()

            result = self._parse_response(content)
            if result is None:
                self.errors += 1
                return None

            self.cache[h] = result
            return result
        except Exception as e:
            self.errors += 1
            err = str(e)
            if "429" in err or "rate" in err.lower():
                print(f"  ⚠️ LLM 429 — rate limit", file=sys.stderr)
            elif "timeout" in err.lower():
                print(f"  ⚠️ LLM timeout", file=sys.stderr)
            else:
                print(f"  ⚠️ LLM: {err[:200]}", file=sys.stderr)
            return None

    def _parse_response(self, content):
        if not content:
            return None
        # Убираем markdown-обёртку ```json ... ```
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        # Ищем первый { ... } (бывает, что модель добавляет текст до/после)
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None

        event_type = data.get("event_type")
        if event_type not in ALLOWED_TYPES:
            event_type = None

        locations = []
        raw_locs = data.get("locations") or []
        if not isinstance(raw_locs, list):
            raw_locs = []
        for loc in raw_locs[:MAX_LOCATIONS]:
            if not isinstance(loc, dict):
                continue
            name = (loc.get("name") or "").strip()
            if not name or len(name) < 3:
                continue
            try:
                confidence = float(loc.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            if confidence < 0.5:
                continue
            locations.append({"name": name, "confidence": confidence})

        return {
            "is_event": bool(data.get("is_event")),
            "event_type": event_type,
            "locations": locations,
        }

    def stats(self):
        return {
            "cache_size": len(self.cache),
            "new_calls": self.new_calls,
            "errors": self.errors,
        }
