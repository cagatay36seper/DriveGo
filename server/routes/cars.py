from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.dependencies.acint import extract_acint_from_request, require_valid_acint
from server.routes.modals import CarDB, CarResponse, ReservationDB


router = APIRouter(prefix="/araclar", tags=["cars"])


def _to_car_response(car: CarDB, musait: bool = True) -> dict:
    return CarResponse.model_validate(
        {
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
            "musait": musait,
        }
    ).model_dump(mode="json")


@router.get("")
def list_cars(request: Request, db: Session = Depends(get_db)):
    require_valid_acint(extract_acint_from_request(request), "cars")
    cars = db.query(CarDB).filter(CarDB.aktif.is_(True)).order_by(CarDB.id.asc()).all()
    return {
        "status": "success",
        "items": [_to_car_response(car, True) for car in cars],
    }


@router.get("/musait")
def get_available_cars(
    request: Request,
    baslangic_tarihi: date | None = Query(default=None),
    bitis_tarihi: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    require_valid_acint(extract_acint_from_request(request), "available cars")
    cars_query = db.query(CarDB).filter(CarDB.aktif.is_(True))

    if baslangic_tarihi and bitis_tarihi:
        if baslangic_tarihi > bitis_tarihi:
            raise HTTPException(status_code=400, detail="Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        reserved_car_ids = (
            db.query(ReservationDB.arac_id)
            .filter(
                ReservationDB.durum != "iptal",
                ReservationDB.baslangic_tarihi < bitis_tarihi,
                ReservationDB.bitis_tarihi > baslangic_tarihi,
            )
            .subquery()
        )

        cars_query = cars_query.filter(~CarDB.id.in_(reserved_car_ids))

    cars = cars_query.order_by(CarDB.id.asc()).all()
    return {
        "status": "success",
        "baslangic_tarihi": baslangic_tarihi,
        "bitis_tarihi": bitis_tarihi,
        "items": [_to_car_response(car, True) for car in cars],
    }


@router.get("/{car_id}")
def get_car(car_id: int, request: Request, db: Session = Depends(get_db)):
    require_valid_acint(extract_acint_from_request(request), "car detail")
    car = db.query(CarDB).filter(CarDB.id == car_id, CarDB.aktif.is_(True)).first()
    if not car:
        raise HTTPException(status_code=404, detail="Araç bulunamadı.")

    return {
        "status": "success",
        "item": _to_car_response(car, True),
    }
