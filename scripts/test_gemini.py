"""Одноразовый тест Gemini. Запускается перед основным парсером."""
import os
import sys
from openai import OpenAI

key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    print("❌ GEMINI_API_KEY не задан в Secrets")
    sys.exit(1)

print(f"🔑 Ключ получен (первые 8 символов: {key[:8]}...)")

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=key,
)

try:
    resp = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[{"role": "user", "content": "Ответь одним словом: работает"}],
        max_tokens=20,
    )
    answer = (resp.choices[0].message.content or "").strip()
    print(f"✅ ОТВЕТ: {answer}")
    print("✅ Gemini доступен, ключ валиден")
except Exception as e:
    print(f"❌ ОШИБКА: {type(e).__name__}: {e}")
    sys.exit(1)
