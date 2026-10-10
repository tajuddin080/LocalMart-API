from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    PID: str = Field(min_length=1, max_length=50)
    PQUANTITY: int = Field(gt=0)


class CartItemQuantityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    PQUANTITY: int = Field(gt=0)


class CartItemResponse(BaseModel):
    PID: str
    PNAME: str
    PQUANTITY: int
    PPRICE: float
    LINE_TOTAL: float


class CartResponse(BaseModel):
    UID: str
    LOCATION: str
    ITEMS: list[CartItemResponse]
    TOTAL_AMOUNT: float


class OrderItemResponse(BaseModel):
    PID: str
    PNAME: str
    PQUANTITY: int
    PPRICE: float
    LINE_TOTAL: float


class OrderResponse(BaseModel):
    OID: int
    UID: str
    WID: str
    LOCATION: str
    STATUS: str
    TOTAL_AMOUNT: float
    CREATED_AT: datetime
    ITEMS: list[OrderItemResponse]
