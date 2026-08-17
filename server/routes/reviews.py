from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from server.db.database import get_db
from server.dependencies.acint import extract_acint_from_request, require_valid_acint
from server.dependencies.auth import require_user
from server.routes.modals import CarDB, ReservationDB, ReviewCreatePayload, ReviewDB, UserDB
from server.utils.sv import RateLimits


router = APIRouter(prefix="/yorumlar", tags=["reviews"])
limiter = Limiter(key_func=get_remote_address)


def _review_response(review: ReviewDB, user: UserDB, car: CarDB, current_user_id: int) -> dict:
    return {
        "id": review.id,
        "arac_id": review.arac_id,
        "puan": review.puan,
        "yorum": review.yorum,
        "author": user.username,
        "car_name": f"{car.marka} {car.model}",
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "mine": review.user_id == current_user_id,
    }


@router.get("")
def list_reviews(
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(extract_acint_from_request(request), "reviews")
    rows = (
        db.query(ReviewDB, UserDB, CarDB)
        .join(UserDB, UserDB.id == ReviewDB.user_id)
        .join(CarDB, CarDB.id == ReviewDB.arac_id)
        .order_by(ReviewDB.updated_at.desc())
        .limit(12)
        .all()
    )
    my_rows = (
        db.query(ReviewDB, UserDB, CarDB)
        .join(UserDB, UserDB.id == ReviewDB.user_id)
        .join(CarDB, CarDB.id == ReviewDB.arac_id)
        .filter(ReviewDB.user_id == current_user.id)
        .all()
    )
    rating_rows = (
        db.query(
            ReviewDB.arac_id,
            func.avg(ReviewDB.puan).label("average"),
            func.count(ReviewDB.id).label("count"),
        )
        .group_by(ReviewDB.arac_id)
        .all()
    )

    return {
        "status": "success",
        "items": [_review_response(review, user, car, current_user.id) for review, user, car in rows],
        "my_items": [_review_response(review, user, car, current_user.id) for review, user, car in my_rows],
        "summaries": {
            str(row.arac_id): {
                "average": round(float(row.average), 1),
                "count": int(row.count),
            }
            for row in rating_rows
        },
    }


@router.post("")
@limiter.limit(RateLimits.API_REVIEWS)
def create_or_update_review(
    payload: ReviewCreatePayload,
    request: Request,
    current_user: UserDB = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_valid_acint(payload.ACInt, "review create")
    require_valid_acint(extract_acint_from_request(request), "review create")

    comment = payload.yorum.strip()
    if len(comment) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Yorum en az 3 karakter olmalıdır.")

    car = db.query(CarDB).filter(CarDB.id == payload.arac_id, CarDB.aktif.is_(True)).first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Araç bulunamadı.")

    user_reservation = (
        db.query(ReservationDB)
        .filter(
            ReservationDB.arac_id == payload.arac_id,
            ReservationDB.user_id == current_user.id,
            ReservationDB.durum == "aktif",
        )
        .first()
    )
    if not user_reservation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yalnızca kendi kiraladığınız araç için yorum yapabilirsiniz.",
        )

    review = (
        db.query(ReviewDB)
        .filter(ReviewDB.arac_id == payload.arac_id, ReviewDB.user_id == current_user.id)
        .first()
    )
    if review:
        review.puan = payload.puan
        review.yorum = comment
    else:
        review = ReviewDB(
            arac_id=payload.arac_id,
            user_id=current_user.id,
            puan=payload.puan,
            yorum=comment,
        )
        db.add(review)

    db.commit()
    db.refresh(review)
    return {
        "status": "success",
        "message": "Değerlendirmeniz kaydedildi.",
        "item": _review_response(review, current_user, car, current_user.id),
    }
