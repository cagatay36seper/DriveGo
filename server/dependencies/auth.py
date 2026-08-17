from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.routes.modals import UserDB
from server.utils.auth import extract_access_token, verify_access_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[UserDB]:
    token = extract_access_token(request)
    payload = verify_access_token(token) if token else None
    if not payload:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return (
        db.query(UserDB)
        .filter(
            UserDB.id == user_id,
            UserDB.is_active.is_(True),
            UserDB.is_blocked.is_(False),
        )
        .first()
    )


def require_user(current_user: Optional[UserDB] = Depends(get_current_user)) -> UserDB:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user
