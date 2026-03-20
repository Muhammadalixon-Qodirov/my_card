# News API Documentation

**Base URL:** `https://mycard.e-investment.uz/api/v1/news`

**Authentication:** Barcha so'rovlarda JWT token kerak:
```
Authorization: Bearer <access_token>
```

---

## Modellar (Schemas)

### News
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated |
| `title` | string | Sarlavha |
| `content` | string | Matn |
| `owner` | integer | Yaratuvchi user ID (read-only) |
| `views_count` | integer | Ko'rganlar soni (read-only) |
| `media` | Media[] | Biriktirilgan media ro'yxati (read-only) |
| `created_at` | datetime | Yaratilgan vaqt (read-only) |

### NewsMedia
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated |
| `media_file` | string (url) | Fayl URL |
| `media_type` | string | `"image"` yoki `"video"` |
| `created_at` | datetime | Yuklangan vaqt (read-only) |

### NewsLog
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Auto-generated |
| `news` | integer | News ID |
| `user` | integer | User ID (read-only, token dan olinadi) |
| `is_read` | boolean | O'qilganmi yoki yo'q |
| `created_at` | datetime | Yaratilgan vaqt (read-only) |

---

## News Endpoints

### 1. Barcha yangiliklar ro'yxati

```
GET /news/
```

**Ruxsat:** Autentifikatsiyadan o'tgan har qanday user

**Query params:** yo'q

**Response `200 OK`:**
```json
[
  {
    "id": 1,
    "title": "Yangi xabar sarlavhasi",
    "content": "Yangilik matni bu yerda...",
    "owner": 3,
    "views_count": 142,
    "media": [
      {
        "id": 1,
        "media_file": "https://mycard.e-investment.uz/media/news_media/photo.jpg",
        "media_type": "image",
        "created_at": "2026-03-20T10:00:00Z"
      },
      {
        "id": 2,
        "media_file": "https://mycard.e-investment.uz/media/news_media/clip.mp4",
        "media_type": "video",
        "created_at": "2026-03-20T10:00:05Z"
      }
    ],
    "created_at": "2026-03-20T10:00:00Z"
  }
]
```

---

### 2. Bitta yangilik

```
GET /news/{id}/
```

**Ruxsat:** Autentifikatsiyadan o'tgan har qanday user

**Path params:**
| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | News ID |

**Response `200 OK`:**
```json
{
  "id": 1,
  "title": "Yangi xabar sarlavhasi",
  "content": "Yangilik matni bu yerda...",
  "owner": 3,
  "views_count": 142,
  "media": [
    {
      "id": 1,
      "media_file": "https://mycard.e-investment.uz/media/news_media/photo.jpg",
      "media_type": "image",
      "created_at": "2026-03-20T10:00:00Z"
    }
  ],
  "created_at": "2026-03-20T10:00:00Z"
}
```

**Response `404 Not Found`:**
```json
{ "detail": "No News matches the given query." }
```

---

### 3. Yangilik yaratish

```
POST /news/
```

**Ruxsat:** Faqat **superuser**

**Content-Type:** `multipart/form-data`

**Body:**
| Field | Type | Majburiy | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Sarlavha |
| `content` | string | ✅ | Matn |
| `media_files` | file[] | ❌ | Rasm yoki video fayllar (bir nechta bo'lishi mumkin) |
| `media_types` | string[] | ❌ | Har bir `media_files` uchun `"image"` yoki `"video"` (bir xil tartibda) |

> **Eslatma:** `media_files[0]` uchun `media_types[0]`, `media_files[1]` uchun `media_types[1]` ko'rsatiladi.
> Agar `media_types` ko'rsatilmasa, default `"image"` qabul qilinadi.

**So'rov misoli (curl):**
```bash
curl -X POST https://mycard.e-investment.uz/api/v1/news/news/ \
  -H "Authorization: Bearer <token>" \
  -F "title=Yangi xabar" \
  -F "content=Xabar matni bu yerda" \
  -F "media_files=@/path/to/photo.jpg" \
  -F "media_types=image" \
  -F "media_files=@/path/to/video.mp4" \
  -F "media_types=video"
```

**Response `201 Created`:**
```json
{
  "id": 5,
  "title": "Yangi xabar",
  "content": "Xabar matni bu yerda",
  "owner": 1,
  "views_count": 0,
  "media": [
    {
      "id": 10,
      "media_file": "https://mycard.e-investment.uz/media/news_media/photo.jpg",
      "media_type": "image",
      "created_at": "2026-03-20T12:00:00Z"
    },
    {
      "id": 11,
      "media_file": "https://mycard.e-investment.uz/media/news_media/video.mp4",
      "media_type": "video",
      "created_at": "2026-03-20T12:00:00Z"
    }
  ],
  "created_at": "2026-03-20T12:00:00Z"
}
```

**Response `400 Bad Request`:**
```json
{ "title": ["This field is required."] }
```

**Response `403 Forbidden`:**
```json
{ "detail": "You do not have permission to perform this action." }
```

---

### 4. Yangilikni to'liq yangilash

```
PUT /news/{id}/
```

**Ruxsat:** Faqat **superuser**

**Content-Type:** `multipart/form-data`

**Path params:**
| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | News ID |

**Body:** (yaratishdagi kabi, barcha fieldlar majburiy)
| Field | Type | Majburiy | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Sarlavha |
| `content` | string | ✅ | Matn |
| `media_files` | file[] | ❌ | Yangi media fayllar (mavjudilariga qo'shiladi) |
| `media_types` | string[] | ❌ | Har bir fayl turi |

**Response `200 OK`:** → yaratishdagi kabi response

---

### 5. Yangilikni qisman yangilash

```
PATCH /news/{id}/
```

**Ruxsat:** Faqat **superuser**

**Content-Type:** `multipart/form-data`

**Body:** (faqat o'zgartirilishi kerak bo'lgan fieldlar)
| Field | Type | Majburiy | Description |
|-------|------|----------|-------------|
| `title` | string | ❌ | Yangi sarlavha |
| `content` | string | ❌ | Yangi matn |
| `media_files` | file[] | ❌ | Qo'shilajak yangi fayllar |
| `media_types` | string[] | ❌ | Yangi fayllar turi |

**Response `200 OK`:** → yaratishdagi kabi response

---

### 6. Yangilikni o'chirish

```
DELETE /news/{id}/
```

**Ruxsat:** Faqat **superuser**

**Path params:**
| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | News ID |

**Response `204 No Content`:** (body bo'sh)

---

## News Logs Endpoints

> Foydalanuvchi yangilikni o'qiganini qayd etish uchun ishlatiladi.
> Har bir `(news, user)` juftligi unikal — bir user bir newsga faqat bitta log yoza oladi.

---

### 7. O'z loglarini ko'rish

```
GET /news-logs/
```

**Ruxsat:** Autentifikatsiyadan o'tgan har qanday user (faqat o'z loglari)

**Query params:**
| Param | Type | Majburiy | Description |
|-------|------|----------|-------------|
| `news` | integer | ❌ | Muayyan news ID bo'yicha filter |

**Misol:**
```
GET /news-logs/?news=3
```

**Response `200 OK`:**
```json
[
  {
    "id": 7,
    "news": 3,
    "user": 12,
    "is_read": true,
    "created_at": "2026-03-20T14:30:00Z"
  }
]
```

---

### 8. Bitta logni ko'rish

```
GET /news-logs/{id}/
```

**Ruxsat:** Autentifikatsiyadan o'tgan user (faqat o'z logi)

**Response `200 OK`:**
```json
{
  "id": 7,
  "news": 3,
  "user": 12,
  "is_read": true,
  "created_at": "2026-03-20T14:30:00Z"
}
```

---

### 9. Yangilikni o'qilgan deb belgilash

```
POST /news-logs/
```

**Ruxsat:** Autentifikatsiyadan o'tgan har qanday user

**Content-Type:** `application/json`

**Body:**
| Field | Type | Majburiy | Description |
|-------|------|----------|-------------|
| `news` | integer | ✅ | News ID |
| `is_read` | boolean | ❌ | O'qilganmi (default: `false`) |

**So'rov misoli:**
```json
{
  "news": 3,
  "is_read": true
}
```

**Xulq-atvor:**
- Agar bu user uchun bu newsda log **mavjud bo'lmasa** → yangi log yaratadi → `201 Created`
- Agar log **mavjud bo'lsa** va `is_read` farq qilsa → yangilanadi → `200 OK`
- Agar log **mavjud bo'lsa** va `is_read` bir xil bo'lsa → o'zgarishsiz qaytaradi → `200 OK`

**Response `201 Created` (yangi log):**
```json
{
  "id": 15,
  "news": 3,
  "user": 12,
  "is_read": true,
  "created_at": "2026-03-20T15:00:00Z"
}
```

**Response `200 OK` (mavjud log yangilandi):**
```json
{
  "id": 15,
  "news": 3,
  "user": 12,
  "is_read": true,
  "created_at": "2026-03-20T15:00:00Z"
}
```

**Response `400 Bad Request`:**
```json
{ "news": ["This field is required."] }
```

---

## HTTP Status Kodlari

| Kod | Ma'no |
|-----|-------|
| `200 OK` | So'rov muvaffaqiyatli |
| `201 Created` | Yangi resurs yaratildi |
| `204 No Content` | O'chirish muvaffaqiyatli |
| `400 Bad Request` | Noto'g'ri ma'lumot yuborildi |
| `401 Unauthorized` | Token yo'q yoki noto'g'ri |
| `403 Forbidden` | Ruxsat yo'q (superuser emas) |
| `404 Not Found` | Resurs topilmadi |
