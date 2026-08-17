# DriveGo Rent a Car

FastAPI, SQLite ve vanilla JavaScript ile hazırlanmış araç kiralama rezervasyon sistemi.

## Özellikler

- Kullanıcı kayıt, giriş, çıkış ve oturum kontrolü
- Araç listeleme ve tarih aralığına göre müsait araç arama
- Rezervasyon oluşturma ve iptal etme
- Dashboard üzerinde kullanıcı, araç ve rezervasyon özetleri
- Basit istek doğrulama ve rate limit koruması

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Uygulama varsayılan olarak `http://localhost:8000` adresinde çalışır.

## Demo Kullanıcı

- E-posta: `admin@admin.com`
- Şifre: `cagatay123`

## Proje Yapısı

- `main.py`: FastAPI uygulama giriş noktası
- `server/db`: veritabanı bağlantısı ve başlangıç verileri
- `server/routes`: API endpoint dosyaları
- `server/dependencies`: ortak doğrulama bağımlılıkları
- `server/utils`: yardımcı servisler
- `client/html`: HTML ve CSS dosyaları
- `client/src`: sayfa JavaScript modülleri
