from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductStockCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    PID: str = Field(min_length=2, max_length=50, pattern=r"^P")
    PNAME: str = Field(min_length=1, max_length=200)
    PPRICE: float = Field(ge=0)
    PQUANTITY: int = Field(ge=0)
    WID: str = Field(min_length=1, max_length=50)

    @field_validator("PID", "PNAME", "WID", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        return value


class ProductStockUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    PID: str = Field(min_length=2, max_length=50, pattern=r"^P")
    WID: str = Field(min_length=1, max_length=50)
    PQUANTITY: int = Field(ge=0)

    @field_validator("PID", "WID", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        return value


class WareHouse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    WID: str = Field(min_length=1, max_length=50)
    LOCATION: str = Field(min_length=1, max_length=100)

    @field_validator("WID", "LOCATION", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        return value
