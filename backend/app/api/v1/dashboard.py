from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.entities import User
from app.schemas.dashboard import (
    AreaView,
    ControlEquation,
    DashboardSummary,
    LiquidityView,
    OverdrawnArea,
    RecentRow,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    data = dashboard_service.summary(db, semester_id)
    return DashboardSummary(
        liquidity=LiquidityView(**data["liquidity"]),
        kassenbereiche=AreaView(**data["kassenbereiche"]),
        control_equation=ControlEquation(**data["control_equation"]),
        overdrawn=[OverdrawnArea(**o) for o in data["overdrawn"]],
        forderungen=data["forderungen"],
        verbindlichkeiten=data["verbindlichkeiten"],
        recent=[
            RecentRow(
                id=t.id, sequential_number=t.sequential_number, date=t.date,
                description=t.description, category=t.category.value, is_storno=t.is_storno,
            )
            for t in data["recent"]
        ],
    )


@router.get("/liquidity", response_model=LiquidityView)
def liquidity(semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return LiquidityView(**dashboard_service.liquidity_view(db, semester_id))


@router.get("/kassenbereiche", response_model=AreaView)
def kassenbereiche(semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return AreaView(**dashboard_service.kassenbereich_view(db, semester_id))


@router.get("/control-equation", response_model=ControlEquation)
def control(semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ControlEquation(**dashboard_service.control_equation_view(db, semester_id))


@router.get("/overdrawn", response_model=list[OverdrawnArea])
def overdrawn(semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [OverdrawnArea(**o) for o in dashboard_service.overdrawn_areas(db, semester_id)]
