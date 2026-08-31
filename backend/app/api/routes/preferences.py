from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user_preference import UserPreference
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate

router = APIRouter(prefix="/me", tags=["me"])

_ALLOWED_DENSITIES = {"comfortable", "compact"}
_THEME_ID_MAX_LEN = 64


@router.get("/preferences", response_model=UserPreferencesResponse)
def get_preferences(
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> UserPreferencesResponse:
    user, _roles = current
    pref = db.get(UserPreference, user.id)
    return UserPreferencesResponse(
        theme_id=pref.theme_id if pref else None,
        density=pref.density if pref else None,
    )


@router.put("/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current: tuple = Depends(get_current_user),
) -> UserPreferencesResponse:
    user, _roles = current
    if payload.density is not None and payload.density not in _ALLOWED_DENSITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"density inválida: {payload.density}",
        )
    if payload.theme_id is not None and len(payload.theme_id) > _THEME_ID_MAX_LEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="themeId inválido"
        )

    pref = db.get(UserPreference, user.id)
    if pref is None:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
    pref.theme_id = payload.theme_id
    pref.density = payload.density
    db.commit()
    db.refresh(pref)
    return UserPreferencesResponse(theme_id=pref.theme_id, density=pref.density)
