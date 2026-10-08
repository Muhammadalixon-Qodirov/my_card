"""Newsbot manbalari ro'yxati.

kind:
    rss      - RSS/Atom feed
    govuz    - gov.uz portal API (`code` — tashkilot kodi)
    links    - feed'i yo'q sahifa: `pattern` ga mos havolalar yangi maqola hisoblanadi
    telegram - kanalning t.me/s/ veb-ko'rinishi (NEWSBOT_USE_TELEGRAM yoqilganda)

general=True — umumiy yangiliklar manbai: faqat kalit so'zga mos kelganlari olinadi.
"""

SOURCES = [
    # O'zbek rasmiy
    {"key": "uzcert", "name": "UZCERT", "kind": "rss", "lang": "uz",
     "url": "https://uzcert.uz/feed/"},
    {"key": "iiv", "name": "Ichki ishlar vazirligi", "kind": "govuz", "lang": "uz",
     "code": "iiv", "general": True},
    {"key": "finlit", "name": "finlit.uz", "kind": "rss", "lang": "uz",
     "url": "https://finlit.uz/uz/articles/rss/", "general": True},

    # O'zbek OAV
    {"key": "kun", "name": "Kun.uz", "kind": "rss", "lang": "uz",
     "url": "https://kun.uz/news/rss?lang=uz", "general": True},
    {"key": "gazeta", "name": "Gazeta.uz", "kind": "rss", "lang": "uz",
     "url": "https://www.gazeta.uz/oz/rss/", "general": True},
    {"key": "spot", "name": "Spot.uz", "kind": "rss", "lang": "uz",
     "url": "https://www.spot.uz/oz/rss/", "general": True},
    {"key": "daryo", "name": "Daryo.uz", "kind": "rss", "lang": "uz",
     "url": "https://daryo.uz/oz/rss-full/", "general": True},
    {"key": "kursiv", "name": "Kursiv Uzbekistan", "kind": "rss", "lang": "uz",
     "url": "https://uz.kursiv.media/uz/feed/", "general": True},
    {"key": "podrobno", "name": "Podrobno.uz", "kind": "rss", "lang": "ru",
     "url": "https://podrobno.uz/rss/", "general": True},

    # Rus tilidagi
    {"key": "kaspersky_scam", "name": "Kaspersky Daily", "kind": "rss", "lang": "ru",
     "url": "https://www.kaspersky.ru/blog/tag/moshennichestvo/feed/"},
    {"key": "kaspersky", "name": "Kaspersky Daily", "kind": "rss", "lang": "ru",
     "url": "https://www.kaspersky.ru/blog/feed/"},
    {"key": "f6", "name": "F6", "kind": "links", "lang": "ru",
     "url": "https://www.f6.ru/media-center/press-releases/",
     "pattern": r'href="(/media-center/press-releases/[^"/]+/)"'},
    {"key": "antimalware", "name": "Anti-Malware.ru", "kind": "rss", "lang": "ru",
     "url": "https://www.anti-malware.ru/news/feed", "general": True},
    {"key": "drweb_mobile", "name": "Dr.Web", "kind": "rss", "lang": "ru",
     "url": "https://news.drweb.ru/rss/get/?c=38&lng=ru"},
    {"key": "ibbank", "name": "BIS Journal", "kind": "rss", "lang": "ru",
     "url": "https://ib-bank.ru/rss", "general": True},

    # Global
    {"key": "groupib", "name": "Group-IB", "kind": "rss", "lang": "en",
     "url": "https://www.group-ib.com/feed/blogfeed/"},
    {"key": "ftc", "name": "FTC Consumer Alerts", "kind": "rss", "lang": "en",
     "url": "https://consumer.ftc.gov/blog/gd-rss.xml"},
    {"key": "ic3", "name": "FBI IC3", "kind": "rss", "lang": "en",
     "url": "https://www.ic3.gov/PSA/RSS"},

    # Telegram (rasmiy o'zbek kanallari)
    {"key": "tg_csec", "name": "Kiberxavfsizlik markazi", "kind": "telegram", "lang": "uz",
     "channel": "cyber_csec_uz", "general": True},
    {"key": "tg_payme", "name": "Payme", "kind": "telegram", "lang": "uz",
     "channel": "payme_uz", "general": True},
    {"key": "tg_uzcard", "name": "Uzcard", "kind": "telegram", "lang": "uz",
     "channel": "uzcard", "general": True},
    {"key": "tg_cbu", "name": "Markaziy bank", "kind": "telegram", "lang": "uz",
     "channel": "centralbankuzbekistan", "general": True},
    {"key": "tg_iiv", "name": "IIV", "kind": "telegram", "lang": "uz",
     "channel": "iivuz", "general": True},
]

SOURCES_BY_KEY = {s["key"]: s for s in SOURCES}
