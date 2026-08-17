from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.dependencies.acint import extract_acint_from_request, require_valid_acint
from server.dependencies.auth import require_user
from server.routes.modals import (
    CarDB,
    ReservationCreatePayload,
    ReservationDB,
    ReservationResponse,
    UserDB,
)


router = APIRouter(prefix="/rezervasyonlar", tags=["reservations"])


def _rental_days(start_date: date, end_date: date) -> int:
    return max((end_date - start_date).days, 1)


def _card_last_four(card_number: str | None) -> str | None:
    if not card_number:
        return None
    digits = "".join(char for char in card_number if char.isdigit())
    return digits[-4:] if len(digits) >= 4 else None


def _is_valid_card_number(card_number: str | None) -> bool:
    digits = "".join(char for char in (card_number or "") if char.isdigit())
    if not 12 <= len(digits) <= 19:
        return False

    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        value = int(digit)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
    return checksum % 10 == 0


def _reservation_response(reservation: ReservationDB, car: CarDB | None = None) -> dict:
    car_data = None
    if car:
        car_data = {
            "id": car.id,
            "marka": car.marka,
            "model": car.model,
            "plaka": car.plaka,
            "yil": car.yil,
            "vites": car.vites,
            "yakit": car.yakit,
            "gunluk_fiyat": car.gunluk_fiyat,
            "image_url": car.image_url,
            "aktif": car.aktif,
            "musait": False,
        }

    return ReservationResponse.model_validate(
        {
            "id": reservation.id,
            "arac_id": reservation.arac_id,
            "user_id": reservation.user_id,
            "baslangic_tarihi": reservation.baslangic_tarihi,
            "bitis_tarihi": reservation.bitis_tarihi,
            "durum": reservation.durum,
            "toplam_tutar": reservation.toplam_tutar,
            "odeme_yontemi": reservation.odeme_yontemi,
            "odeme_durumu": reservation.odeme_durumu,
            "kart_son_dort": reservation.kart_son_dort,
            "created_at": reservation.created_at,
            "car": car_data,
        }
    ).model_dump(mode="json")


@router.get("/benim")
def my_reservations(
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(extract_acint_from_request(request), "my reservations")
    reservations = (
        db.query(ReservationDB)
        .filter(ReservationDB.user_id == current_user.id)
        .order_by(ReservationDB.created_at.desc())
        .all()
    )

    items = []
    for reservation in reservations:
        car = db.query(CarDB).filter(CarDB.id == reservation.arac_id).first()
        items.append(_reservation_response(reservation, car))

    return {"status": "success", "items": items}


@router.post("")
def create_reservation(
    payload: ReservationCreatePayload,
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(payload.ACInt, "reservation create")
    require_valid_acint(extract_acint_from_request(request), "reservation create")

    if payload.baslangic_tarihi > payload.bitis_tarihi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Başlangıç tarihi bitiş tarihinden sonra olamaz.",
        )

    if payload.baslangic_tarihi < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçmiş tarihli rezervasyon oluşturulamaz.",
        )

    car = (
        db.query(CarDB)
        .filter(CarDB.id == payload.arac_id, CarDB.aktif.is_(True))
        .first()
    )
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Araç bulunamadı.")

    conflict = (
        db.query(ReservationDB)
        .filter(
            ReservationDB.arac_id == payload.arac_id,
            ReservationDB.durum != "iptal",
            ReservationDB.baslangic_tarihi < payload.bitis_tarihi,
            ReservationDB.bitis_tarihi > payload.baslangic_tarihi,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seçilen tarihlerde araç zaten rezerve edilmiş.",
        )

    if payload.odeme_yontemi == "kart":
        if not _is_valid_card_number(payload.kart_numarasi):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kart numarası geçerli değil.",
            )
        if not payload.kart_sahibi or len(payload.kart_sahibi.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kart sahibi bilgisi zorunludur.",
            )

    days = _rental_days(payload.baslangic_tarihi, payload.bitis_tarihi)
    total_price = days * float(car.gunluk_fiyat or 0)
    payment_status = "odendi" if payload.odeme_yontemi == "kart" else "beklemede"

    reservation = ReservationDB(
        arac_id=payload.arac_id,
        user_id=current_user.id,
        baslangic_tarihi=payload.baslangic_tarihi,
        bitis_tarihi=payload.bitis_tarihi,
        durum="aktif",
        toplam_tutar=total_price,
        odeme_yontemi=payload.odeme_yontemi,
        odeme_durumu=payment_status,
        kart_son_dort=(
            _card_last_four(payload.kart_numarasi)
            if payload.odeme_yontemi == "kart"
            else None
        ),
    )

    current_user.total_rentals = (current_user.total_rentals or 0) + 1
    current_user.total_spent = (current_user.total_spent or 0) + int(total_price)
    db.add(reservation)
    db.add(current_user)
    db.commit()
    db.refresh(reservation)
    db.refresh(current_user)

    return {
        "status": "success",
        "message": "Rezervasyon oluşturuldu.",
        "reservation": _reservation_response(reservation, car),
    }


@router.post("/{reservation_id}/iptal")
def cancel_reservation(
    reservation_id: int,
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(extract_acint_from_request(request), "reservation cancel")

    reservation = (
        db.query(ReservationDB)
        .filter(
            ReservationDB.id == reservation_id,
            ReservationDB.user_id == current_user.id,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı.")

    reservation.durum = "iptal"
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {
        "status": "success",
        "message": "Rezervasyon iptal edildi.",
        "reservation": _reservation_response(reservation),
    }
