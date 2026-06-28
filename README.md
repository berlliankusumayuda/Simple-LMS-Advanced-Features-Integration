# 📚 LMS Advanced Features & Integration

> **Progress 4 - Pemrograman Sisi Server**  
> Integrasi Redis Caching, MongoDB Analytics, Celery Async Tasks, dan RabbitMQ Message Broker

BERLIAN KUSUMAYUDA - A11.2023.15247

---

## 📋 Daftar Isi

- [Deskripsi Proyek](#-deskripsi-proyek)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Stack Teknologi](#-stack-teknologi)
- [Struktur Proyek](#-struktur-proyek)
- [Fitur Utama](#-fitur-utama)
  - [Redis Caching](#1-redis-caching)
  - [MongoDB Integration](#2-mongodb-integration)
  - [Celery Tasks](#3-celery-tasks)
  - [Rate Limiting](#4-rate-limiting)
  - [Docker Compose](#5-docker-compose)
- [Cara Menjalankan](#-cara-menjalankan)
- [API Endpoints](#-api-endpoints)
- [Monitoring](#-monitoring)
- [Redis CLI Commands](#-redis-cli-commands)
- [Credentials](#-credentials)

---

## 📖 Deskripsi Proyek

Proyek ini merupakan implementasi **Learning Management System (LMS)** dengan advanced features yang mengintegrasikan beberapa teknologi modern untuk meningkatkan performa, skalabilitas, dan kemampuan analitik sistem.

Sistem ini dibangun di atas **Django REST Framework** dan dijalankan menggunakan **Docker Compose** yang mengorkestrasikan **8 services** secara bersamaan.

---

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│                  Web Browser / API Client               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              DJANGO APP (Port 8000)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │           MIDDLEWARE STACK                      │   │
│  │  1. RateLimitMiddleware (60 req/min - Redis)    │   │
│  │  2. ActivityLoggerMiddleware (MongoDB logging)  │   │
│  └─────────────────────────────────────────────────┘   │
└──────┬────────────────┬────────────────┬────────────────┘
       │                │                │
       ▼                ▼                ▼
┌──────────┐    ┌──────────────┐   ┌──────────────┐
│PostgreSQL│    │    Redis     │   │   MongoDB    │
│ Port 5432│    │  Port 6379   │   │  Port 27017  │
│          │    │  DB0: Cache  │   │  activity_   │
│ Users    │    │  DB1: Rate   │   │  logs        │
│ Courses  │    │  DB2: Celery │   │  analytics   │
│Enrollment│    └──────────────┘   └──────────────┘
└──────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              RABBITMQ (Port 5672)                       │
│              Message Broker / Task Queue                │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              CELERY WORKERS                             │
│  ┌──────────────────┐    ┌───────────────────────────┐ │
│  │  Celery Worker   │    │      Celery Beat           │ │
│  │  (4 concurrent)  │    │  (Periodic Scheduler)      │ │
│  └──────────────────┘    └───────────────────────────┘ │
│                                                         │
│  Tasks:                                                 │
│  • send_enrollment_email    • generate_certificate      │
│  • update_course_statistics • export_course_report      │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              FLOWER (Port 5555)                         │
│              Celery Monitoring Dashboard                │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Teknologi

| Komponen | Teknologi | Versi | Port |
|----------|-----------|-------|------|
| Web Framework | Django + DRF | 4.2.9 | 8000 |
| Primary Database | PostgreSQL | 15 | 5432 |
| Cache & Rate Limit | Redis | 7 | 6379 |
| Document Store | MongoDB | 7.0 | 27017 |
| Task Queue | Celery | 5.3.6 | - |
| Message Broker | RabbitMQ | 3.12 | 5672 / 15672 |
| Task Monitoring | Flower | 2.0.1 | 5555 |
| Containerization | Docker Compose | - | - |

---

## 📁 Struktur Proyek

```
lms_project/
│
├── 📄 docker-compose.yml          # Orkestrasi 8 Docker services
├── 📄 Dockerfile                  # Docker image untuk Django app
├── 📄 requirements.txt            # Python dependencies
├── 📄 manage.py                   # Django management script
├── 📄 .env                        # Environment variables (konfigurasi)
│
├── 📁 docs/
│   ├── architecture.md            # Diagram arsitektur + dokumentasi teknis
│   └── redis_cli_commands.md      # Referensi Redis CLI untuk debugging
│
├── 📁 scripts/
│   └── init_mongo.js              # Script inisialisasi indexes MongoDB
│
└── 📁 lms/                        # Django project utama
    ├── __init__.py                # Inisialisasi Celery app
    ├── celery.py                  # Konfigurasi Celery application
    ├── wsgi.py                    # WSGI entry point (Gunicorn)
    ├── urls.py                    # URL routing utama
    │
    ├── 📁 settings/
    │   └── base.py                # Django settings (Redis, MongoDB, Celery config)
    │
    ├── 📁 middleware/
    │   ├── rate_limiter.py        # Sliding Window Rate Limiter (Redis)
    │   └── activity_logger.py     # Async activity logging ke MongoDB
    │
    ├── 📁 tasks/
    │   ├── course_tasks.py        # 4 Celery tasks utama
    │   └── analytics_tasks.py     # Task logging aktivitas
    │
    └── 📁 apps/
        ├── 📁 courses/            # App manajemen kursus
        │   ├── models.py          # Model: Course, Enrollment, Lesson
        │   ├── views.py           # ViewSet + Redis caching logic
        │   ├── admin.py           # Django Admin registration
        │   └── urls.py            # Router endpoints courses
        │
        ├── 📁 analytics/          # App analytics & monitoring
        │   ├── documents.py       # MongoDB MongoEngine document models
        │   ├── cache_service.py   # Redis cache service layer
        │   ├── views.py           # Analytics & aggregation endpoints
        │   └── urls.py
        │
        └── 📁 users/              # App user management
            └── models.py          # Extends Django built-in User
```

---

## ✨ Fitur Utama

### 1. Redis Caching

Implementasi **Cache-Aside Pattern** untuk mempercepat response API.

**3 Database Redis terpisah:**
| Database | Kegunaan | TTL |
|----------|----------|-----|
| DB 0 | Application cache (courses) | 5-30 menit |
| DB 1 | Rate limiting sliding window | 60 detik |
| DB 2 | Celery task result backend | 24 jam |

**Cache Keys:**
```
lms:1:courses:list:{page}:{size}:{search}  → Course list (5 menit)
lms:1:courses:detail:{id}                  → Course detail (10 menit)
lms:1:courses:stats:{id}                   → Course statistics (30 menit)
```

**Cache Invalidation Strategy (Targeted):**
- Saat course diupdate → hapus `detail:{id}` + `stats:{id}` + semua `list:*`
- Saat enrollment terjadi → hapus `detail:{id}` + update `enrollment_count`
- Saat scheduled task jalan → hapus `stats:{id}` jika data berubah

---

### 2. MongoDB Integration

Digunakan untuk **document storage** yang memerlukan schema fleksibel.

**Collections:**

#### `activity_logs`
Menyimpan semua aktivitas user sebagai audit trail.
```json
{
  "user_id": 42,
  "username": "mahasiswa01",
  "action": "course_enroll",
  "resource_type": "course",
  "resource_id": 7,
  "resource_name": "Machine Learning Fundamentals",
  "ip_address": "192.168.1.100",
  "path": "/api/courses/7/enroll/",
  "method": "POST",
  "metadata": {"enrollment_id": 123},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### `course_analytics`
Agregasi statistik per kursus, diupdate oleh Celery Beat.
```json
{
  "course_id": 7,
  "total_enrollments": 150,
  "active_students": 98,
  "completed_students": 45,
  "completion_rate": 30.0,
  "avg_progress": 65.5,
  "last_updated": "2024-01-15T12:00:00Z"
}
```

**Aggregation Queries tersedia:**
- `action_summary` → Hitung aktivitas per tipe action
- `daily_active_users` → DAU 7 hari terakhir
- `top_courses` → Kursus paling banyak diakses

---

### 3. Celery Tasks

Empat async tasks yang diproses oleh Celery Worker melalui RabbitMQ:

#### Task 1: `send_enrollment_email`
```
Trigger: Student enroll ke kursus (POST /api/courses/{id}/enroll/)
Flow   : Buat Enrollment → Kirim task ke RabbitMQ → Worker ambil task
         → Fetch data student & course → Kirim email SMTP → Log ke MongoDB
Retry  : Otomatis hingga 3x jika gagal (interval 60 detik)
```

#### Task 2: `generate_certificate`
```
Trigger: Student menyelesaikan kursus (progress = 100%)
Flow   : Validasi progress → Generate PDF (ReportLab) → Simpan ke /media/
         → Update Enrollment.certificate_issued = True
         → Kirim email dengan attachment PDF → Invalidate Redis cache
Retry  : Otomatis hingga 3x jika gagal (interval 120 detik)
```

#### Task 3: `update_course_statistics` ⏰ Scheduled
```
Trigger: Celery Beat — setiap 30 menit otomatis
Flow   : Fetch semua published courses → Hitung stats dari PostgreSQL
         → Update Course.enrollment_count → Upsert ke MongoDB CourseAnalytics
         → Invalidate Redis cache jika ada perubahan
```

#### Task 4: `export_course_report`
```
Trigger: Instructor request report (POST /api/courses/{id}/report/)
Flow   : Response 202 LANGSUNG + task_id (non-blocking)
         → Worker generate file CSV/Excel (openpyxl)
         → Simpan ke /media/reports/ → Kirim email dengan download URL
Format : CSV (default) atau Excel dengan header styling
Timeout: 5 menit soft limit
```

---

### 4. Rate Limiting

Implementasi **Sliding Window Algorithm** menggunakan Redis Sorted Set.

```
Limit  : 60 requests per menit
Scope  : Per user (authenticated) atau per IP (anonymous)
Storage: Redis DB 1 (sorted set dengan timestamp sebagai score)
```

**Response Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Window: 60
Retry-After: 23  (hanya saat 429)
```

**Response saat limit terlampaui (HTTP 429):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Maksimal 60 request per menit. Coba lagi dalam 23 detik.",
  "retry_after": 23
}
```

---

### 5. Docker Compose

**8 Services yang berjalan:**

| Service | Container | Status |
|---------|-----------|--------|
| Django App | `lms_web` | Port 8000 |
| PostgreSQL | `lms_postgres` | Port 5432, healthcheck ✓ |
| Redis | `lms_redis` | Port 6379, healthcheck ✓ |
| MongoDB | `lms_mongodb` | Port 27017, healthcheck ✓ |
| RabbitMQ | `lms_rabbitmq` | Port 5672 + 15672, healthcheck ✓ |
| Celery Worker | `lms_celery_worker` | 4 concurrent workers |
| Celery Beat | `lms_celery_beat` | Periodic scheduler |
| Flower | `lms_flower` | Port 5555, monitoring UI |

---

## 🚀 Cara Menjalankan

### Prasyarat
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) terinstall dan berjalan
- Git (opsional, untuk clone repo)
- Minimal RAM 4GB free

### Langkah-langkah

**1. Clone atau download repository**
```bash
git clone https://github.com/berlliankusumayuda/Simple-LMS-Advanced-Features-Integration.git
```

**2. Pastikan file `.env` ada**
```bash
# File .env sudah tersedia, cukup sesuaikan jika perlu
# Khususnya EMAIL_HOST_USER dan EMAIL_HOST_PASSWORD jika ingin test email
```

**3. Build dan jalankan semua services**
```bash
docker compose up --build -d
```
> Proses ini memerlukan waktu 2-5 menit saat pertama kali (download images + install packages)

**4. Tunggu semua service healthy (~30-60 detik), lalu cek status**
```bash
docker compose ps
```
Pastikan semua container berstatus `Up` atau `healthy`.

**5. Jalankan database migrations**
```bash
docker compose exec web python manage.py migrate
```

**6. Buat superuser untuk Django Admin**
```bash
docker compose exec web python manage.py createsuperuser
```

**7. Akses aplikasi**

| Layanan | URL | Credential |
|---------|-----|------------|
| Django API | http://localhost:8000 | - |
| Django Admin | http://localhost:8000/admin/ | superuser yang dibuat |
| Health Check | http://localhost:8000/health/ | - |
| Flower Monitor | http://localhost:5555 | - |
| RabbitMQ UI | http://localhost:15672 | `lms_user` / `lms_password` |

### Menghentikan Aplikasi
```bash
# Stop semua container (data tetap tersimpan)
docker compose down

# Stop + hapus semua data (reset total)
docker compose down -v
```

### Melihat Logs
```bash
# Log semua services
docker compose logs -f

# Log service tertentu
docker compose logs -f web
docker compose logs -f celery-worker
docker compose logs -f db
```

---

## 📡 API Endpoints

### Courses

| Method | Endpoint | Deskripsi | Cache |
|--------|----------|-----------|-------|
| GET | `/api/courses/` | List kursus dengan pagination & filter | ✅ 5 menit |
| GET | `/api/courses/{id}/` | Detail kursus + lessons | ✅ 10 menit |
| POST | `/api/courses/` | Buat kursus baru | ❌ (invalidate list) |
| PUT | `/api/courses/{id}/` | Update kursus | ❌ (invalidate cache) |
| POST | `/api/courses/{id}/enroll/` | Enroll ke kursus → trigger email task | ❌ |
| POST | `/api/courses/{id}/report/` | Export report async → response 202 | ❌ |
| GET | `/api/courses/{id}/stats/` | Statistik kursus dari MongoDB | ✅ 30 menit |

**Query Parameters untuk GET `/api/courses/`:**
```
?page=1          → Nomor halaman
?page_size=10    → Jumlah per halaman
?search=python   → Cari berdasarkan judul/deskripsi
?category=tech   → Filter berdasarkan kategori
?status=published→ Filter berdasarkan status
```

**Contoh Response GET `/api/courses/`:**
```json
{
  "count": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "from_cache": true,
  "results": [
    {
      "id": 1,
      "title": "Python for Beginners",
      "slug": "python-for-beginners",
      "description": "...",
      "instructor": {"id": 1, "name": "John Doe"},
      "enrollment_count": 150,
      "price": "0.00",
      "status": "published"
    }
  ]
}
```

**Contoh Response POST `/api/courses/{id}/enroll/`:**
```json
{
  "message": "Berhasil mendaftar!",
  "enrollment_id": 42,
  "course": "Python for Beginners",
  "email_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Analytics

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/analytics/cache-stats/` | Statistik Redis cache |
| GET | `/api/analytics/activity-logs/` | Activity logs dari MongoDB |
| GET | `/api/analytics/aggregations/?type=action_summary` | Aggregation report |
| GET | `/api/analytics/aggregations/?type=daily_active_users` | DAU 7 hari |
| GET | `/api/analytics/aggregations/?type=top_courses` | Top 10 kursus |

### System

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/health/` | Health check |
| GET/POST | `/admin/` | Django Admin Panel |

---

## 📊 Monitoring

### Flower — Celery Task Monitoring
**URL:** `http://localhost:5555`

Fitur yang tersedia:
- 👀 Real-time task status (PENDING / STARTED / SUCCESS / FAILURE / RETRY)
- 📈 Task throughput graph
- 👷 Worker status dan statistik
- 🔍 Detail per task (args, result, traceback jika error)
- ⏱️ Task execution time

### RabbitMQ Management UI
**URL:** `http://localhost:15672`  
**Login:** `lms_user` / `lms_password`

Fitur yang tersedia:
- 📬 Monitor antrian pesan (queue depth)
- 📊 Message rates (publish / deliver / acknowledge per detik)
- 🔀 Exchange dan binding management
- 👥 User dan virtual host management

### Django Admin
**URL:** `http://localhost:8000/admin/`

Kelola data melalui admin panel:
- Users dan Groups
- Courses, Categories, Enrollments, Lessons
- Celery Beat periodic tasks schedule

---

## 🖥️ Redis CLI Commands

Masuk ke Redis CLI:
```bash
docker exec -it lms_redis redis-cli
```

**Monitoring cache:**
```bash
INFO stats                          # Hit rate & statistics
KEYS lms:1:courses:*                # List semua course cache keys
TTL lms:1:courses:detail:1          # Sisa waktu hidup cache
DBSIZE                              # Jumlah keys di database
```

**Cache invalidation manual:**
```bash
DEL lms:1:courses:detail:1          # Hapus cache detail course ID 1
redis-cli KEYS "lms:1:courses:list:*" | xargs redis-cli DEL  # Hapus semua list cache
```

**Rate limiting:**
```bash
SELECT 1                            # Pindah ke database rate limit
KEYS ratelimit:*                    # List semua rate limit entries
ZCARD ratelimit:user:1              # Request count user ID 1
DEL ratelimit:user:1                # Reset rate limit user tertentu
```

**Celery results:**
```bash
SELECT 2                            # Pindah ke database celery results
KEYS celery-task-meta-*             # List semua task results
```

---

## 🔑 Credentials

| Service | Username | Password |
|---------|----------|----------|
| Django Admin | *(dibuat saat createsuperuser)* | *(dibuat saat createsuperuser)* |
| PostgreSQL | `lms_user` | `lms_password` |
| RabbitMQ | `lms_user` | `lms_password` |
| Flower | *(tidak ada auth)* | - |
| MongoDB | *(tanpa auth)* | - |
| Redis | *(tanpa auth)* | - |

> ⚠️ **Catatan:** Credential di atas adalah untuk environment development. Ganti semua password dengan yang lebih kuat sebelum deploy ke production.

---

## 📦 Dependencies Utama

```
Django==4.2.9               # Web framework
djangorestframework==3.14.0 # REST API toolkit
psycopg2-binary==2.9.9      # PostgreSQL adapter
redis==5.0.1                # Redis client
django-redis==5.4.0         # Django Redis cache backend
celery==5.3.6               # Distributed task queue
kombu==5.3.4                # Messaging library (Celery dependency)
pymongo==4.6.1              # MongoDB driver
mongoengine==0.27.0         # MongoDB ODM
flower==2.0.1               # Celery monitoring
Pillow==10.2.0              # Image processing
reportlab==4.0.9            # PDF generation
pandas==2.1.4               # Data manipulation
openpyxl==3.1.2             # Excel file generation
python-decouple==3.8        # Environment variables
django-cors-headers==4.3.1  # CORS handling
gunicorn==21.2.0            # WSGI HTTP Server
django-celery-beat==2.5.0   # Periodic task scheduler
```

---

## 👨‍💻 Informasi Pengembang

**Mata Kuliah:** Pemrograman Sisi Server  
**Tugas:** Progress 4 — Simple LMS Advanced Features & Integration  

**Learning Objectives yang dicapai:**
- ✅ Redis caching patterns (Cache-Aside, Targeted Invalidation)
- ✅ MongoDB integration untuk document storage
- ✅ Asynchronous task processing dengan Celery
- ✅ Message queue dengan RabbitMQ
- ✅ Rate limiting implementation (Sliding Window)
- ✅ Docker Compose orchestration (8 services)
- ✅ Monitoring dengan Flower dan RabbitMQ Management UI
