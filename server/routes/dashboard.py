from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.dependencies.acint import extract_acint_from_request, require_valid_acint
from server.dependencies.auth import require_user
from server.routes.modals import CarDB, ReservationDB, UserDB, UserMeResponse


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard_api(
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(extract_acint_from_request(request), "dashboard")
    total_cars = db.query(func.count(CarDB.id)).scalar() or 0
    active_reservations = (
        db.query(func.count(ReservationDB.id))
        .filter(ReservationDB.durum == "aktif")
        .scalar()
        or 0
    )
    available_cars = (
        db.query(func.count(CarDB.id))
        .filter(CarDB.aktif.is_(True))
        .scalar()
        or 0
    )

    recent_cars = db.query(CarDB).filter(CarDB.aktif.is_(True)).order_by(CarDB.id.desc()).limit(6).all()

    return {
        "status": "success",
        "user": UserMeResponse.model_validate(current_user).model_dump(mode="json"),
        "stats": {
            "total_cars": total_cars,
            "available_cars": available_cars,
            "active_reservations": active_reservations,
        },
        "recent_cars": [
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
                "musait": True,
            }
            for car in recent_cars
        ],
    }
