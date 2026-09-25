from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CalculateRequest(BaseModel):
    gsm: int
    quantity: int
    printing_side: str  # "Single Side" | "Double Side"
    lamination: str  # "None" | "Gloss" | "Matte" | "Velvet"
    use_nearest_quantity: bool = True


class CalculateResponse(BaseModel):
    gsm: int
    quantity: int
    printing_side: str
    lamination: str

    rate_quantity_used: int
    used_nearest_quantity: bool

    printing_min: float
    printing_max: float
    lamination_price: float

    final_min_per_piece: float
    final_max_per_piece: float

    total_min: float
    total_max: float


class OrderCreate(CalculateRequest):
    customer_name: Optional[str] = ""
    customer_phone: Optional[str] = ""
    notes: Optional[str] = ""


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

    customer_name: str
    customer_phone: str
    notes: str

    gsm: int
    quantity: int
    printing_side: str
    lamination: str

    rate_quantity_used: int
    used_nearest_quantity: bool

    printing_min: float
    printing_max: float
    lamination_price: float

    final_min_per_piece: float
    final_max_per_piece: float

    total_min: float
    total_max: float


class RateOptions(BaseModel):
    gsm_options: list[int]
    printing_sides: list[str]
    lamination_options: list[str]
    quantity_brackets: list[int]
