from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint

from server.db.database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    balance = Column(Integer, default=0, nullable=False)
    orders = Column(JSON, default=list, nullable=False)

    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    driver_license_number = Column(String, nullable=True)
    driver_license_expiry = Column(DateTime, nullable=True)
    driver_license_photo = Column(String, nullable=True)

    identity_number = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)

    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)

    total_rentals = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class CarDB(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    marka = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    plaka = Column(String, unique=True, index=True, nullable=False)
    yil = Column(Integer, nullable=True)
    vites = Column(String, nullable=True)
    yakit = Column(String, nullable=True)
    gunluk_fiyat = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    aktif = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReservationDB(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    arac_id = Column(Integer, ForeignKey("cars.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    baslangic_tarihi = Column(Date, nullable=False, index=True)
    bitis_tarihi = Column(Date, nullable=False, index=True)
    durum = Column(String, default="aktif", nullable=False, index=True)
    toplam_tutar = Column(Float, default=0, nullable=False)
    odeme_yontemi = Column(String, default="kart", nullable=False)
    odeme_durumu = Column(String, default="odendi", nullable=False)
    kart_son_dort = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewDB(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("arac_id", "user_id", name="uq_reviews_user_car"),)

    id = Column(Integer, primary_key=True, index=True)
    arac_id = Column(Integer, ForeignKey("cars.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    puan = Column(Integer, nullable=False)
    yorum = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegisterPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr = Field(..., description="E-posta adresi")
    password: str = Field(..., min_length=6, max_length=64)

    full_name: str = Field(..., min_length=2, max_length=100, alias="fullName")
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Turkey"
    zip_code: Optional[str] = None

    driver_license_number: str = Field(..., min_length=5, max_length=20, alias="driverLicense")
    driver_license_expiry: Optional[date] = None
    driver_license_photo: Optional[str] = None

    identity_number: Optional[str] = Field(None, pattern=r"^[0-9]{11}$")
    birth_date: Optional[date] = None

    ACInt: list[Any] = Field(..., min_length=2, max_length=2)

    model_config = ConfigDict(populate_by_name=True)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=64)
    ACInt: list[Any] = Field(..., min_length=2, max_length=2)

    model_config = ConfigDict(populate_by_name=True)


class UserMeResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    driver_license_number: Optional[str] = None
    driver_license_expiry: Optional[date] = None
    driver_license_photo: Optional[str] = None
    identity_number: Optional[str] = None
    birth_date: Optional[date] = None
    is_verified: bool = False
    is_active: bool = True
    is_blocked: bool = False
    balance: int = 0
    total_rentals: int = 0
    total_spent: int = 0
    rating_average: float = 0.0
    orders: Optional[List[Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CarResponse(BaseModel):
    id: int
    marka: str
    model: str
    plaka: str
    yil: Optional[int] = None
    vites: Optional[str] = None
    yakit: Optional[str] = None
    gunluk_fiyat: Optional[float] = None
    image_url: Optional[str] = None
    aktif: bool = True
    musait: bool = True

    model_config = ConfigDict(from_attributes=True)


class ReservationCreatePayload(BaseModel):
    arac_id: int
    baslangic_tarihi: date
    bitis_tarihi: date
    odeme_yontemi: str = Field(default="kart", pattern=r"^(kart|havale|teslimatta)$")
    kart_sahibi: Optional[str] = Field(default=None, max_length=80)
    kart_numarasi: Optional[str] = Field(default=None, max_length=19)
    ACInt: list[Any] = Field(..., min_length=2, max_length=2)

    model_config = ConfigDict(populate_by_name=True)


class ReservationResponse(BaseModel):
    id: int
    arac_id: int
    user_id: Optional[int] = None
    baslangic_tarihi: date
    bitis_tarihi: date
    durum: str
    toplam_tutar: float = 0
    odeme_yontemi: str = "kart"
    odeme_durumu: str = "odendi"
    kart_son_dort: Optional[str] = None
    created_at: datetime
    car: Optional[CarResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewCreatePayload(BaseModel):
    arac_id: int
    puan: int = Field(..., ge=1, le=5)
    yorum: str = Field(..., min_length=3, max_length=500)
    ACInt: list[Any] = Field(..., min_length=2, max_length=2)


class ReviewResponse(BaseModel):
    id: int
    arac_id: int
    puan: int = Field(..., ge=1, le=5)
    yorum: str
    author: str
    car_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    mine: bool = False

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    status: str = "success"
    user: UserMeResponse
    stats: dict[str, Any]
    recent_cars: List[CarResponse] = Field(default_factory=list)
