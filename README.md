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
        +--> AI servis katmanı (yerel Ollama) --> Report + chat
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
cp backend/.env.example backend/.env      # SECRET_KEY'i degistirin
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Backend: http://localhost:8000 (Swagger: `/docs`)
- Frontend: http://localhost:5173
- Ollama: http://localhost:11434

### AI katmanı için modeli indirin

AI rapor/chat katmanı **yerel Ollama** üzerinden çalışır: API anahtarı gerekmez, ücretsizdir ve tarama bulguları makineden dışarı çıkmaz. Container'lar ayağa kalktıktan sonra modeli bir kez indirin:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

Model yaklaşık 2 GB'dır ve `ollama_data` volume'ünde kalır, tekrar indirmeniz gerekmez.

> **Windows/macOS kullanıyorsanız** Ollama'yı [ollama.com/download](https://ollama.com/download) üzerinden doğrudan işletim sistemine kurmak genelde daha iyidir — container'ın aksine GPU'yu kullanabilir, yani rapor üretimi belirgin şekilde hızlanır. Bu durumda `docker compose up` yerine `docker compose up --scale ollama=0` ile compose'daki Ollama'yı devre dışı bırakın ve `backend/.env` içine `OLLAMA_BASE_URL=http://host.docker.internal:11434` yazın. Modeli normal terminalden `ollama pull qwen2.5:3b` ile indirirsiniz. Farklı bir model kullanmak isterseniz `backend/.env` içindeki `OLLAMA_MODEL` değerini değiştirin (`qwen2.5:7b` ve `llama3.1:8b` daha kaliteli ama daha yavaş, `qwen2.5:1.5b` daha hızlı ama daha zayıf).

Ollama çalışmıyorsa veya model indirilmemişse sistem çökmez: bulgulara dayalı, deterministik bir fallback rapor üretilir — yani proje AI katmanı olmadan da uçtan uca çalışır.

> CPU üzerinde çıkarım yavaş olabilir; bir rapor üretimi 1-3 dakika sürebilir. Zaman aşımı `OLLAMA_TIMEOUT` ile ayarlanır (varsayılan 300 sn).

### Sahibi olmadığın bir domain'le denemek istersen

Gerçek bir tarama başlatmak için hedefin DNS TXT kaydıyla doğrulanması gerekir (bkz. aşağıdaki "Kullanım akışı"). Kendi domain'in yoksa iki seçeneğin var:

1. **Demo modu**: `backend/.env` içine `SKIP_TARGET_VERIFICATION=true` ekle, container'ları yeniden başlat. Bu durumda "Doğrulamayı kontrol et" butonu gerçek bir DNS kontrolü yapmadan hedefi doğrular. **Sadece kendi bilgisayarında, tek başına kullanırken aç — başkalarıyla paylaşılan bir ortamda asla açma**, aksi halde herkes sahip olmadığı domainleri "doğrulayıp" tarayabilir.
2. Hedef olarak **`scanme.nmap.org`** kullan — Nmap projesinin, tarama araçlarını denemeniz için açıkça izin verdiği resmi bir test sunucusudur. (Demo modu kapalıyken bile bu domain için TXT kaydı ekleyemeyeceğin için yine `SKIP_TARGET_VERIFICATION=true` gerekir; asıl fayda, taramanın gerçek/anlamlı sonuçlar üretmesidir.)

### Sorun giderme: `backend` container'i "relation ... already exists" hatasiyla cokuyor

Projeyi Alembic migration'lari eklenmeden once bir kez calistirdiysan, Postgres volume'unde tablolar zaten "create_all" ile olusturulmus olabilir. Alembic ayni tablolari sifirdan olusturmaya calisinca cakisir ve backend baslamaz. Yerel gelistirme ortaminda (kaybedecek gercek veri yoksa) en basit cozum, veritabanini sifirlamak:

```bash
docker compose down -v   # Postgres volume'unu da siler
docker compose up --build
```

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
