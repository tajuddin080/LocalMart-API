from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class UserCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    UID: str = Field(min_length=1, max_length=50)
    UEMAIL: EmailStr
    UPWORD: SecretStr = Field(min_length=8, max_length=128)
    LOCATION: str = Field(min_length=1, max_length=100)

    @field_validator("UID", "LOCATION", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("UEMAIL")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserLoginSchema(BaseModel):
    Uemail: EmailStr
    Upword: SecretStr

    @field_validator("Uemail")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    UID: str = Field(min_length=1, max_length=50)
    UEMAIL: EmailStr
    LOCATION: str = Field(min_length=1, max_length=100)

    @field_validator("UID", "LOCATION", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("UEMAIL")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    UID: str
    UEMAIL: EmailStr
    ROLE: str
    LOCATION: str
