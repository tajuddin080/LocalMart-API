from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    UID: str = Field(min_length=1, max_length=50)


class OrderItemResponse(BaseModel):
    PID: str
    PNAME: str
    PQUANTITY: int
    PPRICE: float
    LINE_TOTAL: float


class CheckoutResponse(BaseModel):
    OID: int
    UID: str
    WID: str
    LOCATION: str
    STATUS: str
    TOTAL_AMOUNT: float
    CREATED_AT: datetime
    ITEMS: list[OrderItemResponse]
