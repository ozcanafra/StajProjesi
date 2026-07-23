# SentraScan

pentest-tools.com tarzi otomatik güvenlik tarama araçlarını, **AI destekli risk analizi ve raporlama** katmanıyla birleştiren bir platform. Fark yalnızca "tarama yap ve sonucu göster" değil: ham bulgular AI tarafından sentezlenip önceliklendirilir, iş etkisi ve somut düzeltme adımlarıyla birlikte sunulur, üstüne bulgular hakkında soru-cevap yapılabilir.

## Neden özgün

- **Ham veri değil, risk hikayesi**: Her taramanın sonunda AI, bulguları risk skoru + yönetici özeti + teknik özet + önceliklendirilmiş, remediation önerili bir listeye dönüştürür.
- **Rapor üzerinde sohbet**: Kullanıcı, üretilen rapor hakkında doğal dilde soru sorabilir ("en kritik bulgu neden önemli, nasıl kapatırım?").
- **Yetkilendirme farkındalığı**: Bir hedef, DNS TXT kaydıyla sahiplik doğrulanmadan taranamaz — gerçek bir pentest aracında olması gereken temel bir kısıtlama.
- **Trend farkındalığı**: Her tarama, aynı hedefin bir önceki taramasıyla otomatik kıyaslanır (yeni/kapatılan bulgular, risk skoru değişimi) ve bu bağlam AI özetine de yansıtılır.

## Mimari

```
frontend (React + TS + Tailwind)
        |
        v  REST (JWT)
backend (FastAPI)  ---->  PostgreSQL (kullanıcı/hedef/tarama/bulgu/rapor)
        |
        v  Celery task kuyruğu
worker (Celery)  ---->  Redis (broker)
        |
        +--> scanner modülleri (recon, headers_tls, webvuln)
        +--> AI servis katmanı (Anthropic API) --> Report + chat
```

### Modüller

| Modül | Ne yapar |
|---|---|
| `recon` | crt.sh üzerinden pasif alt alan adı keşfi + hedefin kendi IP'sine karşı sınırlı bir TCP port taraması |
| `headers_tls` | HTTP güvenlik header'ları (HSTS, CSP, X-Frame-Options...), cookie bayrakları, TLS protokol sürümü ve sertifika geçerlilik süresi kontrolü |
| `webvuln` | Eski/güvenlik açıklı JS kütüphaneleri, açık dizin listeleme, hassas dosya sızıntısı (`.git/HEAD`, `.env`), mixed-content ve GET ile şifre gönderen formlar |
| AI rapor katmanı | Yukarıdaki modüllerin ham bulgularını risk skoru + özet + önceliklendirilmiş remediation listesine dönüştürür, ardından bulgular hakkında soru-cevap sağlar |

Tüm kontroller **pasiftir**: aktif exploit denemesi, kimlik doğrulama bypass'ı veya saldırı payload'u içermez.

## Kurulum (Docker Compose)

```bash
cp backend/.env.example backend/.env      # SECRET_KEY'i degistirin, isterseniz ANTHROPIC_API_KEY/ANTHROPIC_MODEL ekleyin
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Backend: http://localhost:8000 (Swagger: `/docs`)
- Frontend: http://localhost:5173

`ANTHROPIC_API_KEY` boş bırakılırsa AI rapor katmanı devre dışı kalmaz; bulgulara dayalı, deterministik bir fallback rapor üretir — yani proje AI anahtarı olmadan da uçtan uca çalışır.

### Sahibi olmadığın bir domain'le denemek istersen

Gerçek bir tarama başlatmak için hedefin DNS TXT kaydıyla doğrulanması gerekir (bkz. aşağıdaki "Kullanım akışı"). Kendi domain'in yoksa iki seçeneğin var:

1. **Demo modu**: `backend/.env` içine `SKIP_TARGET_VERIFICATION=true` ekle, container'ları yeniden başlat. Bu durumda "Doğrulamayı kontrol et" butonu gerçek bir DNS kontrolü yapmadan hedefi doğrular. **Sadece kendi bilgisayarında, tek başına kullanırken aç — başkalarıyla paylaşılan bir ortamda asla açma**, aksi halde herkes sahip olmadığı domainleri "doğrulayıp" tarayabilir.
2. Hedef olarak **`scanme.nmap.org`** kullan — Nmap projesinin, tarama araçlarını denemeniz için açıkça izin verdiği resmi bir test sunucusudur. (Demo modu kapalıyken bile bu domain için TXT kaydı ekleyemeyeceğin için yine `SKIP_TARGET_VERIFICATION=true` gerekir; asıl fayda, taramanın gerçek/anlamlı sonuçlar üretmesidir.)

Şema, `backend` container'ı ayağa kalkarken otomatik olarak `alembic upgrade head` ile oluşturulur/güncellenir — ayrıca bir şey yapmana gerek yok.

### Veritabanı migrationları

Modellerde değişiklik yaptıktan sonra yeni bir migration üretmek için (backend klasöründe, venv aktifken):
```bash
alembic revision --autogenerate -m "kisa aciklama"
alembic upgrade head
```

## Yerel gelistirme (Docker'siz)

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL/REDIS_URL'i localhost'a gore duzenleyin
alembic upgrade head   # semayi olustur/guncelle
uvicorn app.main:app --reload
```

Ayrı bir terminalde Celery worker:
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Kullanım akışı

1. Kayıt ol / giriş yap
2. Bir hedef domain ekle
3. Verilen DNS TXT kaydını domain'e ekleyip "Doğrulamayı kontrol et" ile sahiplik doğrulamasını tamamla
4. Modülleri seçip taramayı başlat (arka planda Celery worker çalışır)
5. Tarama tamamlanınca AI risk raporunu incele, rapor hakkında soru sor
6. İstersen raporu PDF olarak indir

## Yol haritası

- [x] Aynı hedefin geçmiş taramaları arasında trend/diff analizi (`GET /api/scans/{id}/diff`, AI özetine trend bağlamı besleniyor)
- [x] Ek pasif web-vuln kontrolleri (`webvuln` modülü: eski JS kütüphaneleri, açık dizin listeleme, hassas dosya sızıntısı, güvensiz form ayarları)
- [x] PDF rapor export (`GET /api/scans/{id}/report.pdf`, frontend'de "PDF indir" butonu)
- [x] Alembic ile şema migration yönetimi (`backend/alembic/`, `docker-compose` backend servisi başlamadan `alembic upgrade head` çalıştırır)
