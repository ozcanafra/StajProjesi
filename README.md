# SentraScan

pentest-tools.com tarzi otomatik güvenlik tarama araçlarını, **AI destekli risk analizi ve raporlama** katmanıyla birleştiren bir platform. Fark yalnızca "tarama yap ve sonucu göster" değil: ham bulgular AI tarafından sentezlenip önceliklendirilir, iş etkisi ve somut düzeltme adımlarıyla birlikte sunulur, üstüne bulgular hakkında soru-cevap yapılabilir.

## Neden özgün

- **Ham veri değil, risk hikayesi**: Her taramanın sonunda AI, bulguları risk skoru + yönetici özeti + teknik özet + önceliklendirilmiş, remediation önerili bir listeye dönüştürür.
- **Rapor üzerinde sohbet**: Kullanıcı, üretilen rapor hakkında doğal dilde soru sorabilir ("en kritik bulgu neden önemli, nasıl kapatırım?").
- **Yetkilendirme farkındalığı**: Bir hedef, DNS TXT kaydıyla sahiplik doğrulanmadan taranamaz — gerçek bir pentest aracında olması gereken temel bir kısıtlama.

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
        +--> scanner modülleri (recon, headers_tls)
        +--> AI servis katmanı (Anthropic API) --> Report + chat
```

### Modüller

| Modül | Ne yapar |
|---|---|
| `recon` | crt.sh üzerinden pasif alt alan adı keşfi + hedefin kendi IP'sine karşı sınırlı bir TCP port taraması |
| `headers_tls` | HTTP güvenlik header'ları (HSTS, CSP, X-Frame-Options...), cookie bayrakları, TLS protokol sürümü ve sertifika geçerlilik süresi kontrolü |
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

## Yerel gelistirme (Docker'siz)

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL/REDIS_URL'i localhost'a gore duzenleyin
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

## Yol haritası

- Aynı hedefin geçmiş taramaları arasında trend/diff analizi
- Ek pasif web-vuln kontrolleri (eski JS kütüphaneleri, açık dizin listeleme)
- PDF rapor export
- Alembic ile şema migration yönetimi
