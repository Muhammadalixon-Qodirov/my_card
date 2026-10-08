import json
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_SOURCE_CHARS = 6000
UZBEKISTAN = re.compile(r"o.?zbek|uzbek|узбек|ўзбек", re.I)

SYSTEM_PROMPT = """Sen MyCard ilovasining kiberxavfsizlik muharririsan. O'quvchilaring — O'zbekistondagi oddiy bank kartasi va smartfon foydalanuvchilari, ular texnik mutaxassis emas.

Senga bitta manba materiali beriladi (o'zbek, rus yoki ingliz tilida). Ikki ish qil.

1. Material o'quvchiga kerakmi, hal qil.
"relevant": true — faqat material quyidagilardan biri haqida bo'lsa VA o'quvchi o'zini himoya qilish uchun biror narsa qila olsa:
- firibgarlik sxemasi (soxta qo'ng'iroq, soxta sayt, soxta yutuq, soxta to'lov va h.k.);
- fishing, bank kartasi, to'lov ilovasi yoki SMS kodni o'g'irlash;
- Telegram, WhatsApp yoki boshqa akkauntni egallab olish;
- telefon uchun zararli ilova yoki fayl;
- oddiy foydalanuvchilarga tegishli ma'lumot sizib chiqishi;
- keng tarqalgan qurilma va ilovalardagi (Android, iPhone, Telegram, WhatsApp, brauzer) shoshilinch xavf.
"relevant": false — reklama, aksiya, tadbir, konferensiya, musobaqa, kompaniya yangiligi, mahsulot taqdimoti, amaliy maslahatsiz statistika, qonunchilik yangiligi, server va tarmoq uskunalari (Cisco, Fortinet, WordPress va shunga o'xshash) zaifligi, sxemasi tushuntirilmagan jinoyat xronikasi, O'zbekistonda ishlamaydigan chet el kompaniyasining ichki hodisasi, kiberxavfsizlikka aloqasi yo'q material.

2. Agar relevant bo'lsa, o'zbek tilida (lotin yozuvida) post yoz.
Qoidalar:
- Faqat manbadagi faktlardan foydalan. Manbada yo'q raqam, ism, havola, telefon raqami yoki voqea qo'shma.
- Voqea qaysi davlatda bo'lganini manbadagidek ayt. Manbada O'zbekiston tilga olinmagan bo'lsa, "O'zbekiston" so'zini umuman ishlatma. Chet el banki yoki idorasi nomini umumlashtir ("bank xodimi", "davlat idorasi").
- Sodda so'zlar bilan yoz, atamalarni tushuntir. Qo'rqitma, bo'rttirma.
- "content" tuzilishi: avval 1-2 gapda nima bo'layotgani; keyin "Qanday aldashadi:" bo'limi; keyin "O'zingizni qanday himoya qilasiz:" bo'limi va 3-5 ta qisqa band, har biri "• " bilan boshlanadi.
- Oddiy matn: markdown, HTML, emoji va havola ishlatma. Uzunligi 600-1500 belgi.
- "title": 90 belgidan qisqa, aniq, bosh harflar bilan baqirmasdan.

Javobni faqat shu JSON ko'rinishida ber:
{"relevant": true yoki false, "reason": "o'zbek tilida bir gapda sabab", "title": "...", "content": "..."}
relevant false bo'lsa, title va content bo'sh satr bo'lsin."""


class LLMError(Exception):
    pass


class LLMRateLimited(LLMError):
    pass


def _parse(content: str) -> dict:
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < 0:
        raise LLMError(f"JSON topilmadi: {content[:200]}")
    try:
        data = json.loads(content[start:end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"JSON xato: {exc}") from exc
    return {
        "relevant": data.get("relevant") is True,
        "reason": str(data.get("reason") or "")[:500],
        "title": str(data.get("title") or "").strip()[:255],
        "content": str(data.get("content") or "").strip(),
    }


def review(*, source_name: str, title: str, text: str) -> dict:
    if not settings.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY sozlanmagan")

    payload = {
        "model": settings.NEWSBOT_GROQ_MODEL,
        "temperature": 0.2,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Manba: {source_name}\nSarlavha: {title}\n\nMatn:\n{text[:MAX_SOURCE_CHARS]}"},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    for attempt in range(3):
        try:
            response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=90)
        except requests.RequestException as exc:
            raise LLMError(f"Groq so'rovi bajarilmadi: {exc}") from exc
        if response.status_code == 429:
            wait = min(float(response.headers.get("retry-after") or 20), 60)
            logger.warning("Groq limit, %s soniya kutiladi", wait)
            time.sleep(wait)
            continue
        if response.status_code >= 400:
            raise LLMError(f"Groq {response.status_code}: {response.text[:300]}")
        result = _parse(response.json()["choices"][0]["message"]["content"] or "")
        if result["relevant"] and not (result["title"] and result["content"]):
            raise LLMError("Model relevant dedi, lekin matn bermadi")
        if result["relevant"] and UZBEKISTAN.search(f"{result['title']}\n{result['content']}") \
                and not UZBEKISTAN.search(f"{title}\n{text}"):
            raise LLMError("AI manbada yo'q bo'lgan O'zbekistonni qo'shdi")
        return result
    raise LLMRateLimited("Groq limiti tugadi")
