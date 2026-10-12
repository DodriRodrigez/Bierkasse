from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import Money


class MoneyRow(BaseModel):
    id: str
    name: str
    type: str
    balance: Money


class LiquidityView(BaseModel):
    items: list[MoneyRow]
    total: Money


class AreaRow(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool
    balance: Money


class AreaView(BaseModel):
    items: list[AreaRow]
    total: Money


class ControlEquation(BaseModel):
    sum_kassenbereiche: Money
    liquiditaet: Money
    forderungen: Money
    verbindlichkeiten: Money
    expected: Money
    difference: Money
    balanced: bool


class OverdrawnArea(BaseModel):
    id: str
    name: str
    balance: Money
    overdraft: Money


class RecentRow(BaseModel):
    id: str
    sequential_number: int
    date: date
    description: str
    category: str
    is_storno: bool


class DashboardSummary(BaseModel):
    liquidity: LiquidityView
    kassenbereiche: AreaView
    control_equation: ControlEquation
    overdrawn: list[OverdrawnArea]
    forderungen: Money
    verbindlichkeiten: Money
    recent: list[RecentRow]
