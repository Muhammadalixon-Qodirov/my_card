import html
import io
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from PIL import Image

logger = logging.getLogger(__name__)

TASHKENT = ZoneInfo("Asia/Tashkent")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}
GOVUZ_API = "https://api-portal.gov.uz/authorities/news"
DATE_FORMATS = (
    "%B %d, %Y | %I:%M%p",       # FTC
    "%Y-%m-%d %H:%M:%S",         # gov.uz
)


@dataclass
class RawItem:
    url: str
    title: str = ""
    text: str = ""
    published_at: datetime | None = None
    image_url: str = ""


def _is_image(url: str, hint: str = "") -> bool:
    return hint.startswith("image") or bool(re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", url, re.I))


def _first_image(markup: str) -> str:
    match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', markup or "", re.I)
    return html.unescape(match.group(1)) if match else ""


def http_get(url: str, headers: dict | None = None) -> str:
    for attempt in range(2):
        try:
            response = requests.get(url, headers={**HEADERS, **(headers or {})}, timeout=30)
            break
        except requests.ConnectionError:
            if attempt:
                raise
            time.sleep(3)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "tr", "blockquote"}
    SKIP = {"script", "style", "noscript", "svg", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def parse_date(value: str | None) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    parsed = None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        for fmt in DATE_FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TASHKENT)
    return parsed


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def fetch_rss(source: dict) -> list[RawItem]:
    root = ET.fromstring(http_get(source["url"]).lstrip("﻿ \r\n\t").encode("utf-8"))
    items = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        fields, image = {}, ""
        for child in node:
            name = _local(child.tag)
            if name in ("enclosure", "content", "thumbnail") and child.get("url"):
                if not image and _is_image(child.get("url"), child.get("type") or child.get("medium") or ""):
                    image = child.get("url")
            elif name == "link" and child.get("href"):
                fields.setdefault("link", child.get("href"))
            elif name not in fields or name == "encoded":
                fields[name] = "".join(child.itertext()) if len(child) else (child.text or "")
        url = (fields.get("link") or fields.get("guid") or fields.get("id") or "").strip()
        if not url.startswith("http"):
            continue
        body = fields.get("encoded") or fields.get("content") or fields.get("description") or fields.get("summary") or ""
        items.append(RawItem(
            url=url,
            title=html_to_text(fields.get("title", "")).replace("\n", " "),
            text=html_to_text(body),
            published_at=parse_date(fields.get("pubdate") or fields.get("published")
                                    or fields.get("updated") or fields.get("date")),
            image_url=image or _first_image(body),
        ))
    return items


def fetch_govuz(source: dict) -> list[RawItem]:
    headers = {"code": source["code"], "language": "oz"}
    data = json.loads(http_get(f"{GOVUZ_API}/category?code_name=news&page=1", headers))
    return [
        RawItem(
            url=f"https://gov.uz/oz/{source['code']}/news/view/{row['id']}",
            title=row.get("title", ""),
            text=html_to_text(row.get("anons", "")),
            published_at=parse_date(row.get("date")),
            image_url=row.get("anons_image") or "",
        )
        for row in data.get("data", [])
    ]


def fetch_links(source: dict) -> list[RawItem]:
    page = http_get(source["url"])
    links = dict.fromkeys(re.findall(source["pattern"], page))
    return [RawItem(url=urljoin(source["url"], link)) for link in links]


def fetch_telegram(source: dict) -> list[RawItem]:
    channel = source["channel"]
    page = http_get(f"https://t.me/s/{channel}")
    items = []
    for chunk in page.split('data-post="')[1:]:
        post = re.match(r'[^"/]+/(\d+)"', chunk)
        date = re.search(r'<time datetime="([^"]+)"', chunk)
        body = re.search(
            r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>\s*'
            r'(?:<div class="tgme_widget_message_(?:footer|reactions|info)'
            r'|<a class="tgme_widget_message_(?:link_preview|reply))', chunk, re.S,
        ) or re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', chunk, re.S)
        if not post or not body:
            continue
        text = html_to_text(body.group(1))
        photo = re.search(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", chunk)
        items.append(RawItem(
            url=f"https://t.me/{channel}/{post.group(1)}",
            title=text.split("\n", 1)[0][:200],
            text=text,
            published_at=parse_date(date.group(1)) if date else None,
            image_url=photo.group(1) if photo else "",
        ))
    return items


FETCHERS = {
    "rss": fetch_rss,
    "govuz": fetch_govuz,
    "links": fetch_links,
    "telegram": fetch_telegram,
}


def fetch_source(source: dict) -> list[RawItem]:
    return FETCHERS[source["kind"]](source)


def fetch_article(source: dict, url: str) -> tuple[str, str, str]:
    """Maqola sahifasidan (sarlavha, matn, rasm manzili) oladi."""
    if source["kind"] == "govuz":
        news_id = url.rstrip("/").rsplit("/", 1)[-1]
        data = json.loads(http_get(f"{GOVUZ_API}/view?id={news_id}",
                                   {"code": source["code"], "language": "oz"})).get("data", {})
        image = data.get("body_image") or data.get("anons_image") or ""
        return data.get("title", ""), html_to_text(data.get("body", "")), image

    page = http_get(url)
    og_image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', page, re.I) \
        or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page, re.I)
    image = urljoin(url, html.unescape(og_image.group(1))) if og_image else ""
    heading = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or re.search(r"<title[^>]*>(.*?)</title>", page, re.S)
    title = html_to_text(heading.group(1)).replace("\n", " ") if heading else ""
    paragraphs = (html_to_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", page, re.S))
    text = "\n".join(p for p in paragraphs if len(p) > 60)
    return html.unescape(title), text, image


MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}


def download_image(url: str) -> tuple[bytes, str]:
    """Rasmni yuklab, haqiqatan rasm ekanini tekshiradi. (baytlar, kengaytma) qaytaradi."""
    response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    response.raise_for_status()
    data = response.raw.read(MAX_IMAGE_BYTES + 1, decode_content=True)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Rasm juda katta")
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
        extension = IMAGE_EXTENSIONS.get(image.format)
    if not extension:
        raise ValueError(f"Qo'llanmaydigan format: {image.format}")
    return data, extension
