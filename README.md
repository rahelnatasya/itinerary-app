# Jakarta Weekend Route Optimizer 🗺️🚀

**Submission Final - INaAI Competition 2026** **Role:** Full-stack Developer / AI Engineer  
**Peserta:** Rahel N Pangaribuan  

---

## 📌 Deskripsi Proyek

**Jakarta Weekend Route Optimizer** adalah aplikasi web kolaboratif berbasis AI yang dirancang untuk membantu sekelompok teman merencanakan liburan akhir pekan mereka di Jakarta secara efisien. Pengguna dapat menyusun *wishlist* destinasi bersama secara *real-time*, melakukan *voting*, dan membiarkan AI mengoptimalkan rute perjalanan, estimasi anggaran, serta moda transportasi umum terbaik (MRT Jakarta & Transjakarta).

Aplikasi ini dibangun dengan fokus pada performa tinggi, skalabilitas, dan penanganan konkurensi tingkat lanjut menggunakan arsitektur *event-driven* yang sepenuhnya di-container-isasi dengan Docker.

---

## 🚀 Akses Demo Aplikasi (Jaringan Lokal / LAN)

Karena proyek ini dikonfigurasi untuk kebutuhan Live Defense dan demonstrasi kolaboratif langsung di hadapan juri, aplikasi dapat diakses melalui jaringan lokal (LAN) Wi-Fi yang sama pada tautan berikut:

🔗 **Link Akses Frontend:** [http://192.168.15.225:3000/](http://192.168.15.225:3000/)  
🔗 **Link Dokumentasi API (Swagger/FastAPI):** [http://192.168.15.225:8000/docs](http://192.168.15.225:8000/docs)

---

## ✨ Fitur Utama & Keunggulan Teknis

### 1. Frictionless Authentication (JWT) 🔐
* **Tanpa Formulir Panjang:** Tidak menggunakan registrasi email/password tradisional yang memperlambat UX. Pengguna cukup memasukkan nama panggilan pada *Strict Gatekeeper Modal* saat pertama kali masuk.
* **Keamanan Kriptografi:** Di belakang layar, nama ditukar dengan token JWT (*Stateless Bearer Token*) yang aman, disimpan di `localStorage`, dan dilampirkan pada setiap tajuk (*Header Authorization*) untuk memvalidasi aksi pengguna.

### 2. Kolaborasi Real-Time via Server-Sent Events (SSE) ⚡
* **0ms Latency Delay:** Mekanisme *polling* manual (SWR 3 detik) telah digantikan sepenuhnya oleh **SSE (Server-Sent Events)** dari FastAPI. 
* **Push Notification:** Server secara aktif mendorong perubahan data (ketika teman lain menambah destinasi atau memilih suara) langsung ke Next.js secara instan tanpa perlu memuat ulang halaman.

### 3. Sistem Kunci Validasi Suara (Strict Voting Lock) 🗳️
* **Satu Pengguna = Satu Suara:** Untuk mencegah manipulasi rute AI, setiap pengguna hanya memiliki 1 hak suara mutlak per *Itinerary Room*. Jika pengguna sudah memilih Destinasi A, ia tidak bisa memilih Destinasi B kecuali ia membatalkan (*unlike*) pilihan pertamanya. Validasi ini dikunci rapat di sisi backend menggunakan data dari token JWT.

### 4. Penanganan Race Condition (Optimistic Locking) 🏁
* **Integritas Data:** Menggunakan kolom `version` pada pangkalan data PostgreSQL. Jika dua pengguna melakukan penyuntingan secara bersamaan pada destinasi yang sama, sistem akan mendeteksi konflik konkurensi, menolak *request* kedua dengan status **HTTP 409 (Conflict)**, dan memunculkan *alert* preventif agar data tidak tertimpa diam-diam.

### 5. Asynchronous AI Processing & Task Queue 🧠
* **Non-blocking Thread:** Pemanggilan LLM eksternal (Gemini API) membutuhkan waktu 5-10 detik. FastAPI mendelegasikan tugas berat ini ke **Redis Task Queue**.
* **Background Worker:** Pekerja latar belakang mengambil antrean tugas dari Redis, memproses optimasi rute, dan memperbarui status pangkalan data menjadi `completed` secara asinkron sehingga sistem utama tetap responsif.

---

## 🛠️ Tech Stack & Arsitektur

Aplikasi ini menggunakan pemisahan layanan makro (*multi-service architecture*) yang dihubungkan melalui jaringan Docker Compose:

* **Frontend (Layer 1):** Next.js (React), Tailwind CSS, SWR & EventSource (SSE Client).
* **Backend (Layer 2):** FastAPI (Python) - Mendukung operasi asinkron penuh (`async/await`).
* **Database:** PostgreSQL (Penyimpanan data relasional terstruktur: Trip → Destination → Vote).
* **Message Broker & Cache:** Redis (Antrean tugas analitik AI).
* **Worker (Layer 3):** Python Celery/Custom Background Worker (Eksekusi pipeline LLM).
* **Infrastruktur:** Docker Compose (Automated Orchestration).

---

## 📦 Cara Menjalankan secara Lokal (Quick Start)

Pastikan Anda telah memasang **Docker** dan **Docker Compose** di mesin Anda.

1. Clone repositori ini:
2. Konfigurasikan file lingkungan .env di folder root utama:
   Cuplikan kode
   GEMINI_API_KEY=KUNCI_API_GEMINI_ANDA
   JWT_SECRET_KEY=KUNCI_RAHASIA_KRIPTOGRAFI_UNTUK_JWT
3. Jalankan seluruh layanan dari clean state hanya dengan satu perintah berikut:
   docker compose up -d --build
4. Tunggu beberapa saat hingga semua kontainer berstatus Started. Layanan frontend akan otomatis tersedia di http://localhost:3000 dan backend di http://localhost:8000.
