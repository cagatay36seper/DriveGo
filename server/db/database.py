import os
from datetime import date

import bcrypt
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "webch.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


CAR_SEED_DATA = [
    {
        "marka": "BMW",
        "model": "320i M Sport",
        "plaka": "34DG001",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Benzin",
        "gunluk_fiyat": 3850,
        "image_url": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Mercedes-Benz",
        "model": "C 200 AMG",
        "plaka": "34DG002",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Benzin",
        "gunluk_fiyat": 4250,
        "image_url": "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Audi",
        "model": "Q5 Quattro",
        "plaka": "34DG003",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Dizel",
        "gunluk_fiyat": 4650,
        "image_url": "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Volkswagen",
        "model": "Golf 1.5 eTSI",
        "plaka": "34DG004",
        "yil": 2023,
        "vites": "Otomatik",
        "yakit": "Benzin",
        "gunluk_fiyat": 2450,
        "image_url": "https://www.lloydmotorgroup.com/VehicleLibrary/6229-HlS1YL4jBE2RCWvugLdAzQ.jpg?height=648.75&heightratio=0.75&mode=crop&upscale=true&width=865",
    },
    {
        "marka": "Ford",
        "model": "Transit Custom",
        "plaka": "34DG005",
        "yil": 2023,
        "vites": "Manuel",
        "yakit": "Dizel",
        "gunluk_fiyat": 3150,
        "image_url": "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Hyundai",
        "model": "Tucson Elite",
        "plaka": "34DG006",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Dizel",
        "gunluk_fiyat": 2950,
        "image_url": "https://images.unsplash.com/photo-1619767886558-efdc259cde1a?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Toyota",
        "model": "Corolla Hybrid",
        "plaka": "34DG007",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Hibrit",
        "gunluk_fiyat": 2650,
        "image_url": "https://images.unsplash.com/photo-1623869675781-80aa31012a5a?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Renault",
        "model": "Clio Icon",
        "plaka": "34DG008",
        "yil": 2023,
        "vites": "Otomatik",
        "yakit": "Benzin",
        "gunluk_fiyat": 1850,
        "image_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Fiat",
        "model": "Egea Cross",
        "plaka": "34DG009",
        "yil": 2023,
        "vites": "Manuel",
        "yakit": "Dizel",
        "gunluk_fiyat": 1950,
        "image_url": "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Tesla",
        "model": "Model Y Long Range",
        "plaka": "34DG010",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Elektrik",
        "gunluk_fiyat": 5200,
        "image_url": "https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Porsche",
        "model": "Macan",
        "plaka": "34DG011",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Benzin",
        "gunluk_fiyat": 7900,
        "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=900&q=80",
    },
    {
        "marka": "Range Rover",
        "model": "Evoque",
        "plaka": "34DG012",
        "yil": 2024,
        "vites": "Otomatik",
        "yakit": "Dizel",
        "gunluk_fiyat": 6900,
        "image_url": "https://cdn.wheel-size.com/automobile/body/land-rover-range-rover-evoque-2023-2025-1733916429.4292598.jpg",
    },
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def ensure_schema_updates():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "cars" not in table_names:
        return

    car_columns = {column["name"] for column in inspector.get_columns("cars")}
    if "image_url" not in car_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE cars ADD COLUMN image_url VARCHAR"))

    if "reservations" in table_names:
        reservation_columns = {column["name"] for column in inspector.get_columns("reservations")}
        reservation_updates = {
            "toplam_tutar": "ALTER TABLE reservations ADD COLUMN toplam_tutar FLOAT DEFAULT 0 NOT NULL",
            "odeme_yontemi": "ALTER TABLE reservations ADD COLUMN odeme_yontemi VARCHAR DEFAULT 'kart' NOT NULL",
            "odeme_durumu": "ALTER TABLE reservations ADD COLUMN odeme_durumu VARCHAR DEFAULT 'odendi' NOT NULL",
            "kart_son_dort": "ALTER TABLE reservations ADD COLUMN kart_son_dort VARCHAR",
        }
        with engine.begin() as connection:
            for column_name, statement in reservation_updates.items():
                if column_name not in reservation_columns:
                    connection.execute(text(statement))


def seed_initial_data():
    from server.routes.modals import CarDB, ReservationDB, UserDB

    ensure_schema_updates()
    db = SessionLocal()
    try:
        demo_admin_password = os.getenv("DEMO_ADMIN_PASSWORD")
        if db.query(UserDB).count() == 0 and demo_admin_password:
            admin_user = UserDB(
                username="admin",
                email="admin@admin.com",
                hashed_password=hash_password(demo_admin_password),
                role="admin",
                balance=0,
                orders=[],
                full_name="Admin User",
                is_verified=True,
                is_active=True,
                is_blocked=False,
            )
            db.add(admin_user)

        existing_cars = {car.plaka: car for car in db.query(CarDB).all()}
        for car_data in CAR_SEED_DATA:
            car = existing_cars.get(car_data["plaka"])
            if car:
                for key, value in car_data.items():
                    setattr(car, key, value)
                car.aktif = True
                db.add(car)
            else:
                db.add(CarDB(**car_data, aktif=True))

        if db.query(ReservationDB).count() == 0:
            car = db.query(CarDB).filter(CarDB.plaka == "34DG001").first()
            if car:
                db.add(
                    ReservationDB(
                        arac_id=car.id,
                        user_id=None,
                        baslangic_tarihi=date.today(),
                        bitis_tarihi=date.today(),
                        durum="aktif",
                        toplam_tutar=car.gunluk_fiyat or 0,
                        odeme_yontemi="kart",
                        odeme_durumu="odendi",
                        kart_son_dort="0000",
                    )
                )

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[Seed] Hata oluştu: {exc}")
    finally:
        db.close()
