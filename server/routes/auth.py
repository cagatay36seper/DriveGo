import os
from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from server.db.database import get_db, hash_password
from server.dependencies.acint import extract_acint_from_request, require_valid_acint
from server.dependencies.auth import require_user
from server.routes.modals import LoginPayload, RegisterPayload, UserDB, UserMeResponse
from server.utils.auth import create_access_token
from server.utils.sv import RateLimits


router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _user_response(user: UserDB) -> dict:
    return UserMeResponse.model_validate(user).model_dump(mode="json")


def _set_auth_cookie(response: Response, user: UserDB) -> str:
    token = create_access_token(
        {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "1" if os.getenv("PRODUCTION", "false").lower() in {"1", "true", "yes"} else "0") == "1",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return token


@router.post("/register")
@limiter.limit(RateLimits.API_REGISTER)
async def register(payload: RegisterPayload, request: Request, db: Session = Depends(get_db)):
    require_valid_acint(payload.ACInt, payload.username)

    username = payload.username.strip()
    email = payload.email.lower()

    if db.query(UserDB).filter(UserDB.username == username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This username is already taken.")

    if db.query(UserDB).filter(UserDB.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This email address is already registered.")

    hashed_pwd = hash_password(payload.password)
    new_user = UserDB(
        username=username,
        email=email,
        hashed_password=hashed_pwd,
        role="user",
        balance=0,
        orders=[],
        full_name=payload.full_name,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        country=payload.country,
        zip_code=payload.zip_code,
        driver_license_number=payload.driver_license_number,
        driver_license_expiry=payload.driver_license_expiry,
        driver_license_photo=payload.driver_license_photo,
        identity_number=payload.identity_number,
        birth_date=payload.birth_date,
        is_verified=False,
        is_active=True,
        is_blocked=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Kullanıcı kaydı başarıyla tamamlandı.",
            "user": _user_response(new_user),
        },
    )
    _set_auth_cookie(response, new_user)
    return response


@router.post("/login")
@limiter.limit(RateLimits.API_LOGIN)
async def login(payload: LoginPayload, request: Request, db: Session = Depends(get_db)):
    require_valid_acint(payload.ACInt, payload.email)

    user = db.query(UserDB).filter(UserDB.email == payload.email.lower()).first()
    if not user or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if not bcrypt.checkpw(payload.password.encode("utf-8"), user.hashed_password.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "Giriş başarılı.",
            "user": _user_response(user),
        },
    )
    _set_auth_cookie(response, user)
    return response


@router.get("/me")
async def me(request: Request, current_user: UserDB = Depends(require_user)):
    require_valid_acint(extract_acint_from_request(request), "me")
    return {
        "status": "success",
        "user": _user_response(current_user),
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    require_valid_acint(extract_acint_from_request(request), "logout")
    response.delete_cookie("access_token", path="/")
    return {"status": "success", "message": "Çıkış yapıldı."}
