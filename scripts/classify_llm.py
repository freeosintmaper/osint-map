import json
import os
import re
import sys
import time
import hashlib

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
LLM_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"
PROMPT_VERSION = "v6_settlement_gated_place_evidence"


SYSTEM_PROMPT = """Ты — OSINT-аналитик. Анализируешь посты из Telegram-каналов о войне в Украине.
Отвечай ТОЛЬКО валидным JSON, без markdown, без пояснений.

Формат:
{
  "is_event": true|false,
  "event_type": "Air Raid Alert"|"Military Strike"|"Military Offensive"|"Military Operation"|"Political Development"|null,
  "locations": [{
    "name": "название населённого пункта",
    "country": "UA"|"RU"|null,
    "confidence": 0.0-1.0,
    "specific_place": "явно упомянутая улица, гражданский район, перекрёсток или общедоступный ориентир либо null",
    "evidence": "короткая дословная цитата из поста, подтверждающая specific_place, либо null"
  }, ...]
}

Правила:
- is_event=true ТОЛЬКО если в тексте описано конкретное военное/политическое событие, произошедшее сейчас или недавно.
- is_event=false для: аналитики, мнений, исторических справок (2010-2021), рекламы, анонсов фильмов, постов про другие страны (Йемен, Мали, Сирия, Индонезия, Африка), шуток, рассуждений.
- event_type — строго из списка выше.
- locations — ТОЛЬКО реальные города/НП, где произошло событие. НЕ включай:
  * слова-омонимы (Житель, Лесной, Мирный, Сторона, Долины, Украинское, Городской, Спутник, Селища — это НЕ города в данном контексте)
  * названия областей (Брянская, Черниговская) — используй город-центр области (Брянск, Чернигов)
  * страны, регионы, направления фронта
  * места, где живёт/служит автор поста
  * Не выдавай области, административные районы и громады (например, «Нікопольська громада») за отдельный населённый пункт. В name указывай реальный город/НП, где произошло событие. При этом конкретно названный городской район/микрорайон можно указать отдельно в specific_place только при дословной цитате с самим названием.
- Поле name должно быть реальным городом/населённым пунктом, а не названием парка, кампуса, станции метро, улицы, здания или другого ориентира. Если не можешь определить город/НП, не подменяй его названием ориентира.
- Если локаций нет — пустой массив.
- Если событие охватывает несколько городов — перечисли все.
- country — ОБЯЗАТЕЛЬНО указывай страну города: "UA" (Украина) или "RU" (Россия).
  ВАЖНО: есть города-двойники (Новомосковск, Первомайск, Александрия и др.) в обеих странах.
  Определяй по контексту: "Днепропетровской области", "Харьковской области", "ВСУ" → UA.
  "Тульской области", "Брянской области", "ВС РФ" → RU.
- confidence — насколько уверен, что это локация события (0.0-1.0).
- Если в самом посте явно названы конкретная гражданская улица, район, перекрёсток или общедоступный ориентир, укажи название в specific_place и короткую ДОСЛОВНУЮ цитату в evidence.
- Сама цитата evidence ОБЯЗАТЕЛЬНО должна содержать конкретное название из specific_place и подтверждать именно это место. Цитаты вроде «там», «рядом», «атакованный мост» или «цех, где производят…» без самого названия не подтверждают specific_place.
- Не используй общие описания вместо названий: «большой завод», «мастерская», «терминал», «объект», «склад», «логистический центр» без уникального имени. Если явного названия нет — specific_place=null и evidence=null.
- НИКОГДА не выдумывай адреса, районы, ориентиры или координаты. Не выводи точное место из догадок, фотографий, направления полёта или общих фраз.
- Не извлекай точные места военных позиций, подразделений, штабов, военных/логистических объектов и целей удара или атаки. Если названный объект описывается как цель, по которой нанесли удар, оставляй только населённый пункт.
- evidence должна присутствовать в тексте публикации дословно; если название места не содержится в этой цитате или цитата не подтверждает место, используй specific_place=null и evidence=null."""


def _text_hash(text):
    # Match every input that can affect classification; old cache entries use a
    # different hash and will be recomputed automatically.
    payload = "\n".join((
        PROMPT_VERSION,
        LLM_MODEL,
        SYSTEM_PROMPT,
        text[:1500],
    )).encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


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
                    cached = json.load(f)
                # Previous cache versions used shorter MD5 keys. Drop them so
                # stale results do not consume the new cache's size limit.
                if isinstance(cached, dict):
                    self.cache = {
                        key: value for key, value in cached.items()
                        if isinstance(key, str) and re.fullmatch(r"[0-9a-f]{64}", key)
                    }
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
        """None = LLM недоступна или ошибка (парсер уйдёт на regex-fallback).
        dict = успешный ответ LLM."""
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
            time.sleep(0.3)
            return result
        except Exception as e:
            self.errors += 1
            err_str = str(e)
            if "429" in err_str:
                print(f"  ⚠️ LLM 429 — rate limit / out of capacity", file=sys.stderr)
            elif "timeout" in err_str.lower():
                print(f"  ⚠️ LLM timeout", file=sys.stderr)
            else:
                print(f"  ⚠️ LLM: {err_str[:200]}", file=sys.stderr)
            return None

    def _parse_response(self, content):
        if not content:
            return None
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
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
            country = loc.get("country")
            if country not in ("UA", "RU"):
                country = None
            specific_place = loc.get("specific_place")
            evidence = loc.get("evidence")
            if not isinstance(specific_place, str) or not specific_place.strip():
                specific_place = None
            else:
                specific_place = specific_place.strip()[:160]
            if not isinstance(evidence, str) or not evidence.strip():
                evidence = None
            else:
                evidence = evidence.strip()[:240]
            locations.append({
                "name": name,
                "country": country,
                "confidence": confidence,
                "specific_place": specific_place,
                "evidence": evidence,
            })

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
