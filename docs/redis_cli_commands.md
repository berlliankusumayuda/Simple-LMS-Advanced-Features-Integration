# Redis CLI Commands - LMS Documentation
# Panduan perintah Redis untuk debugging dan monitoring cache LMS

## Cara Masuk ke Redis CLI
```bash
# Via Docker
docker exec -it lms_redis redis-cli

# Atau langsung
redis-cli -h localhost -p 6379
```

---

## 1. MONITORING & INFO

### Cek status Redis
```bash
PING
# Response: PONG

INFO server           # Info server Redis
INFO clients          # Jumlah client yang terkoneksi
INFO memory           # Penggunaan memori
INFO stats            # Statistik hits/misses
INFO keyspace         # Info per database
```

### Cek cache hit rate
```bash
INFO stats | grep keyspace_hits
INFO stats | grep keyspace_misses
# Hit rate = hits / (hits + misses) * 100
```

### Monitor real-time commands
```bash
MONITOR
# Menampilkan semua perintah yang masuk secara real-time
# CTRL+C untuk berhenti
```

---

## 2. KEY MANAGEMENT

### List semua LMS cache keys
```bash
# Database 0 (default cache)
SELECT 0
KEYS lms:1:courses:*

# List semua keys
KEYS *

# Hitung jumlah keys
DBSIZE
```

### Cek key tertentu
```bash
# Cek apakah key ada
EXISTS lms:1:courses:detail:1

# Cek TTL (time to live) dalam detik
TTL lms:1:courses:detail:1
# -1 = tidak ada expiry
# -2 = key tidak ada
# angka positif = sisa waktu hidup

# Cek tipe data
TYPE lms:1:courses:detail:1

# Lihat value
GET lms:1:courses:detail:1
```

---

## 3. CACHE INVALIDATION

### Hapus cache course tertentu
```bash
# Hapus cache detail satu course
DEL lms:1:courses:detail:1

# Hapus cache statistics satu course
DEL lms:1:courses:stats:1

# Hapus multiple keys sekaligus
DEL lms:1:courses:detail:1 lms:1:courses:detail:2
```

### Hapus semua course list cache (pattern delete)
```bash
# Script bash untuk pattern delete
redis-cli KEYS "lms:1:courses:list:*" | xargs redis-cli DEL

# Atau menggunakan SCAN untuk performa lebih baik (production)
redis-cli --scan --pattern "lms:1:courses:list:*" | xargs redis-cli DEL
```

### Hapus semua cache LMS
```bash
# HATI-HATI: Akan hapus SEMUA cache!
redis-cli KEYS "lms:1:*" | xargs redis-cli DEL

# Atau flush entire database (lebih drastis)
FLUSHDB       # Flush database saat ini
FLUSHALL      # Flush SEMUA database (jangan dilakukan di production!)
```

---

## 4. RATE LIMITING (Database 1)

```bash
SELECT 1   # Pindah ke database rate_limit

# Lihat semua rate limit keys
KEYS ratelimit:*

# Cek request count untuk user tertentu
ZCARD ratelimit:user:1        # Jumlah request user ID 1
ZCARD ratelimit:ip:127.0.0.1  # Jumlah request dari IP

# Lihat detail timestamps request
ZRANGE ratelimit:user:1 0 -1 WITHSCORES

# Reset rate limit untuk user/IP tertentu
DEL ratelimit:user:1
DEL ratelimit:ip:192.168.1.100

# Cek TTL rate limit key
TTL ratelimit:user:1
```

---

## 5. CELERY RESULT BACKEND (Database 2)

```bash
SELECT 2   # Pindah ke database celery results

# List semua task results
KEYS celery-task-meta-*

# Lihat result task tertentu (ganti dengan task ID)
GET celery-task-meta-a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Hapus result task lama
DEL celery-task-meta-a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## 6. PERFORMANCE MONITORING

### Memory usage per key
```bash
# Cek ukuran value untuk key tertentu
MEMORY USAGE lms:1:courses:detail:1
# Response dalam bytes

# Debug object (compression info)
DEBUG OBJECT lms:1:courses:detail:1
```

### Slow log (query yang lambat)
```bash
SLOWLOG GET 10     # Ambil 10 query paling lambat
SLOWLOG LEN        # Jumlah entries di slow log
SLOWLOG RESET      # Reset slow log
```

### Latency monitoring
```bash
LATENCY HISTORY event    # History latency
LATENCY LATEST           # Latency terbaru
LATENCY RESET            # Reset latency history
```

---

## 7. USEFUL SCRIPTS

### Script: Lihat semua cache dengan TTL
```bash
#!/bin/bash
# Tampilkan semua LMS cache keys dengan TTL
redis-cli KEYS "lms:1:*" | while read key; do
    ttl=$(redis-cli TTL "$key")
    echo "$key -> TTL: ${ttl}s"
done
```

### Script: Cache statistics summary
```bash
#!/bin/bash
echo "=== LMS Redis Cache Statistics ==="
echo ""
echo "-- Database Sizes --"
for db in 0 1 2; do
    count=$(redis-cli -n $db DBSIZE)
    echo "DB $db: $count keys"
done
echo ""
echo "-- Cache Hit Rate --"
redis-cli INFO stats | grep -E "keyspace_(hits|misses)"
echo ""
echo "-- Memory Usage --"
redis-cli INFO memory | grep -E "used_memory_human|used_memory_peak_human"
```

### Script: Warm up cache (populate cache setelah restart)
```bash
#!/bin/bash
# Panggil endpoints untuk populate cache
echo "Warming up course list cache..."
curl -s http://localhost:8000/api/courses/ > /dev/null
curl -s http://localhost:8000/api/courses/?page=2 > /dev/null
echo "Cache warm-up complete!"
```

---

## 8. CACHE KEY REFERENCE

| Key Pattern | Database | TTL | Keterangan |
|-------------|----------|-----|------------|
| `lms:1:courses:list:*` | 0 | 300s | Course list dengan filter |
| `lms:1:courses:detail:{id}` | 0 | 600s | Course detail |
| `lms:1:courses:stats:{id}` | 0 | 1800s | Course statistics |
| `ratelimit:user:{id}` | 1 | 120s | Rate limit per user |
| `ratelimit:ip:{ip}` | 1 | 120s | Rate limit per IP |
| `celery-task-meta-{uuid}` | 2 | 86400s | Celery task results |
