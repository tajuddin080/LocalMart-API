from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import UserDetails
from user_service.schemas import (
    UserCreateSchema,
    UserLoginSchema,
    UserResponse,
    UserUpdateSchema,
)
from user_service.security import hash_password, is_hashed_password, verify_password

u_router = APIRouter()


@u_router.get("/greeting")
def greeting():
    return "Hello"


@u_router.post("/login", response_model=UserResponse)
def user_login(u_data: UserLoginSchema, db: Session = Depends(get_db)):
    stmt = select(UserDetails).where(UserDetails.UEMAIL == u_data.Uemail)
    user = db.scalars(stmt).first()
    stored_password = user.UPWORD if user is not None else None

    if stored_password is None or not verify_password(
        u_data.Upword.get_secret_value(),
        stored_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not is_hashed_password(stored_password):
        user.UPWORD = hash_password(u_data.Upword.get_secret_value())
        db.commit()
        db.refresh(user)

    return user


@u_router.post(
    "/adduser",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user(u_data: UserCreateSchema, db: Session = Depends(get_db)):
    stmt = select(UserDetails).where(
        or_(
            UserDetails.UID == u_data.UID,
            UserDetails.UEMAIL == u_data.UEMAIL,
        )
    )
    if db.scalars(stmt).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User ID or email already exists",
        )

    user = UserDetails(
        UID=u_data.UID,
        UEMAIL=u_data.UEMAIL,
        UPWORD=hash_password(u_data.UPWORD.get_secret_value()),
        ROLE="customer",
        LOCATION=u_data.LOCATION,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User ID or email already exists",
        ) from None
    db.refresh(user)
    return user


@u_router.put(
    "/update_user",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def update_user_details(updated_data: UserUpdateSchema, db: Session = Depends(get_db)):
    stmt = select(UserDetails).where(UserDetails.UID == updated_data.UID)
    user = db.scalars(stmt).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    duplicate_email_stmt = select(UserDetails).where(
        UserDetails.UEMAIL == updated_data.UEMAIL,
        UserDetails.UID != updated_data.UID,
    )
    if db.scalars(duplicate_email_stmt).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    user.UEMAIL = updated_data.UEMAIL
    user.LOCATION = updated_data.LOCATION
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from None
    db.refresh(user)
    return user


@u_router.delete("/delete_user", status_code=status.HTTP_200_OK)
def delete_user(u_id: str, db: Session = Depends(get_db)):
    stmt = select(UserDetails).where(UserDetails.UID == u_id)
    user = db.scalars(stmt).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
