---
title: Book News Scraping — Product Card
doc_id: CARD-book-news-scraping
doc_type: product-card
verdict: showcase
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# Book News Scraping — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

เก็บข่าวธุรกิจและเทคโนโลยีไทยจาก feed สาธารณะ (Matichon, NotebookSpec, Bangkok Post Business, Blognone) เข้า data lake และให้ API อ่านอย่างเดียว

## 2. ปัญหาและผู้ใช้เป้าหมาย

- ปัญหา: ติดตามข่าวไทยหลายแหล่งในที่เดียวแบบตรวจย้อนได้
- ผู้ใช้: operator/agent ภายใน Solo Empire **[ต้องยืนยัน]** consumer จริง

## 3. สิ่งที่ทำได้จริงตอนนี้

- `scripts/run_feeds.py` + `news/feed_adapter.py` (FeedSpec ต่อแหล่ง) และ feed เสริมแบบ opt-in
- `news_data/api.py` ให้ `news.v1` อ่านอย่างเดียว; refresh token เทียบแบบ constant-time
- replay เข้า Bronze ผ่าน `task scraping:ingest -- --product news` และ `task scraping:news:run`
- 18 test files ครอบคลุม parser, HTTP, API

## 4. หลักฐานสถานะ

| รายการ | ค่า (ตรวจจาก repository) |
|---|---|
| Stack | Python |
| Commits | 18 (แรก 2026-07-09 → ล่าสุด 2026-10-01) |
| Source | 25 ไฟล์ / 2,193 บรรทัด |
| Tests | 18 ไฟล์ |
| CI | 1 workflow |
| Deploy config | ไม่มี |
| Live URL | ไม่มี |
| README | 141 บรรทัด (`book-news-scraping`) |
| โครงสร้างซ้ำ (template family) | 1 repo ที่มี structure signature เดียวกัน |

## 5. คุณค่าและจุดต่าง

- เป็นตัวอย่าง feed collector → lake → API ที่ครบวงจรและเล็กพอให้อ่าน
- มุมรายได้: news digest ภาษาไทยเฉพาะกลุ่ม **[สมมติฐาน]** — ตลาด aggregator มีเจ้าใหญ่อยู่แล้ว

## 6. ช่องว่างสำคัญ

- `book-job-scraping` ยังเก็บ feed เดียวกันในฐานะ compatibility runner (ซ้ำซ้อน)
- ไม่มี consumer/digest ที่ใช้ข้อมูลจริง

## 7. คำตัดสิน

**`showcase`** — เป็นหลักฐาน portfolio ที่ดีและเป็นเจ้าของโดเมนข่าวที่ถูกต้อง แต่ยังไม่ใช่ผลิตภัณฑ์ จะเป็น `invest` เมื่อมี digest/consumer ที่มีผู้อ่านประจำ

## 8. ขั้นต่อไป

1. ถอด news feed ออกจาก scheduler ของ `book-job-scraping`
2. ตัดสินว่ามี consumer ใดจะอ่าน `news.v1`

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `PRODUCT.md`
- `scripts/run_feeds.py`
- `news/feed_adapter.py`
- `news_data/api.py`
