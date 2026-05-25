# BLUEPRINT & PROMPT GUIDE: Collaborative Smart Itinerary Planner
**Tujuan:** MVP web app event-driven untuk kompetisi INaAI (Batas Waktu: 21,5 Jam).
**Fokus Utama (Juri Must Haves):** Dockerized, Clean Code (SOLID), Event-Driven Architecture, Race Condition Handling (Optimistic Locking).

---

## 1. TECH STACK & ARSITEKTUR
- **Frontend:** Next.js (App Router), Tailwind CSS, SWR (untuk polling).
- **Backend:** FastAPI (Python), SQLAlchemy (ORM).
- **Database:** PostgreSQL.
- **Message Broker:** Redis + RQ (Redis Queue) untuk background worker.
- **Infrastruktur:** Docker Compose (4 service: frontend, backend, db, redis).
- **QA:** Cypress (E2E testing, dikerjakan terakhir jika waktu cukup).

---

## 2. DATABASE SCHEMA

### Table `trips`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | UUID, PK | |
| `title` | String | |
| `status` | String | `"draft"` / `"processing"` / `"completed"` / `"failed"` |
| `ai_insight` | JSONB | Hasil dari worker. Nullable sampai analisis selesai. |
| `version` | Integer, Default 1 | **Krusial untuk optimistic locking** |
| `created_at` | Timestamp | |

### Table `destinations`
| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | UUID, PK | |
| `trip_id` | UUID, FK | |
| `name` | String | |
| `added_by` | String | Nama user statis (tidak perlu auth) |
| `notes` | Text | Nullable |
| `order_index` | Integer | Urutan destinasi dalam rute |
| `is_feasible` | Boolean | Diisi oleh worker setelah analisis AI |
| `version` | Integer, Default 1 | **Krusial untuk optimistic locking** |

---

## 3. KONTRAK API (Single Source of Truth Frontend ↔ Backend)

Agent wajib mengikuti shape ini persis. Jangan improvise.

### `POST /api/trips/{id}/analyze`
**Request body:** kosong  
**Response 200:**
```json
{ "trip_id": "uuid", "status": "processing" }
```
**Response 409 (jika sudah processing):**
```json
{ "detail": "Trip is already being processed." }
```

### `GET /api/trips/{id}`
**Response 200:**
```json
{
  "id": "uuid",
  "title": "string",
  "status": "draft|processing|completed|failed",
  "version": 1,
  "ai_insight": null,
  "destinations": [
    { "id": "uuid", "name": "string", "order_index": 1, "is_feasible": true, "version": 1 }
  ]
}
```

### `PUT /api/destinations/{id}`
**Request body:**
```json
{ "name": "string", "notes": "string", "version": 2 }
```
**Response 200:** objek destination terupdate  
**Response 409:**
```json
{ "detail": "Conflict: destination was updated by another user. Please refresh." }
```

---

## 4. SCOPE BATASAN (Strict Rules for AI Agent)

- **TIDAK PERLU** sistem autentikasi/login — gunakan field `added_by` dengan nama statis atau input bebas.
- **TIDAK PERLU** integrasi Google Maps API — LLM cukup return JSON berisi urutan dan flag `is_feasible`.
- **WAJIB** optimistic locking di SQLAlchemy: jika `request.version != db.version`, lempar HTTP 409.
- **WAJIB** pisahkan logika AI ke worker terpisah via Redis agar endpoint FastAPI tidak blocking.
- **WAJIB** idempotency di endpoint analyze: jika status trip sudah `"processing"`, kembalikan 409 dengan pesan di atas — jangan buat job baru.
- **WAJIB** tambahkan status `"failed"` di tabel trips: jika worker error, set status ke `"failed"` bukan biarkan stuck di `"processing"`.
- **JANGAN** gunakan `time.sleep()` di worker — simulasi LLM cukup dengan `return` hardcoded JSON berikut:
```json
{
  "summary": "Rute optimal untuk 1 hari: mulai dari Kawah Putih, lanjut ke Situ Patenggang.",
  "feasible_destinations": ["Kawah Putih", "Situ Patenggang"],
  "removed_destinations": ["Pantai Pelabuhan Ratu"],
  "removal_reason": "Jarak terlalu jauh, estimasi 4.5 jam dari titik sebelumnya.",
  "ordered_route": ["Kawah Putih", "Situ Patenggang"]
}
```

---

## 5. URUTAN PROMPTING KE AGENT

### Tahap 0: Konfirmasi Arsitektur
> "Sebelum menulis kode apapun: tampilkan folder structure lengkap yang akan kamu buat untuk monorepo ini. Sertakan nama file utama di setiap folder. Jangan tulis kode dulu, konfirmasi dulu strukturnya."

### Tahap 1: Setup Infrastruktur & Boilerplate
> "Buat monorepo dengan folder `frontend` (Next.js App Router, Tailwind) dan `backend` (FastAPI). Di root, buat `docker-compose.yml` dengan 4 service: `frontend`, `backend`, `db` (Postgres image: postgres:15), dan `redis` (image: redis:7-alpine). Tambahkan health check untuk db dan redis. Pastikan semua container bisa di-build dan saling ping. Jangan tulis logika bisnis dulu."

### Tahap 2a: Database Models & Koneksi
> "Di folder `backend`, setup SQLAlchemy dengan koneksi ke Postgres. Buat dua model sesuai schema di panduan (Trips dan Destinations) lengkap dengan kolom `version` (int default 1) untuk optimistic locking. Terapkan prinsip SOLID: pisahkan models, database connection, dan repository pattern ke file terpisah."

### Tahap 2b: Endpoints & Optimistic Locking
> "Buat tiga endpoint FastAPI sesuai kontrak API. Untuk `PUT /api/destinations/{id}`: implementasikan optimistic locking — bandingkan `request.version` dengan `db.version`, jika beda lempar HTTP 409. Untuk `POST /api/trips/{id}/analyze`: cek dulu apakah status trip sudah `'processing'` — jika iya, lempar 409. Pisahkan routing, service layer, dan repository ke file berbeda."

### Tahap 3: Event-Driven Worker
> "Tambahkan RQ (Redis Queue) di FastAPI. Endpoint `POST /api/trips/{id}/analyze` hanya perlu: (1) set status trip menjadi `'processing'`, (2) enqueue job ke Redis, (3) return `{'trip_id': id, 'status': 'processing'}`. Buat file `worker/tasks.py` terpisah yang berisi satu fungsi: ambil `trip_id`, fetch semua destinations dari DB, return hardcoded JSON AI insight (tanpa sleep). Setelah return JSON: parse hasilnya, update field `is_feasible` di setiap destination, update `ai_insight` di trips, set status trip menjadi `'completed'`. Jika error, set ke `'failed'`."

### Tahap 4: Frontend UI & Polling
> "Di `frontend`, buat satu halaman utama bergaya board sederhana. Tampilkan daftar destinations dan status trip saat ini. Gunakan SWR dengan interval 3 detik untuk polling `GET /api/trips/{id}`. Handle tiga state status ('processing' = spinner, 'completed' = hasil AI, 'failed' = error alert). Saat user mengedit destination dan mendapat error 409, tampilkan alert merah 'Destinasi diperbarui orang lain'. Saat klik 'Generate Itinerary', disable tombol jika status masih processing."

---

## 6. DEMO SCRIPT (Untuk Presentasi ke Juri)

Urutan demo yang memperlihatkan semua fitur kritis:
1. Buka dua browser tab berbeda (simulasi dua user).
2. Di Tab A, tambahkan 3 destinasi.
3. Di Tab B, edit destinasi yang sama di Tab A secara bersamaan.
4. **Tunjukkan:** Tab B mendapat error 409 (Race condition handling).
5. Di Tab A, klik "Generate Itinerary".
6. **Tunjukkan:** status berubah ke "processing", spinner muncul.
7. **Tunjukkan:** polling mendeteksi status "completed" dan hasil AI muncul otomatis.
8. Coba klik "Generate Itinerary" saat processing — **tunjukkan:** tombol disabled.