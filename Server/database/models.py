from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase,mapped_column,Mapped
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String

class Base(DeclarativeBase):
    pass


class UserDetails(Base):

    __tablename__= "UserDetails"

    UID : Mapped[String] = mapped_column(String,primary_key=True)
    UEMAIL : Mapped[String] = mapped_column(String,nullable=False,unique=True)
    UPWORD : Mapped[String] = mapped_column(String)
    ROLE:Mapped[String] = mapped_column(String)
    LOCATION: Mapped[String] = mapped_column(String)

class ProductDetails(Base):
    __tablename__ = "ProductDetails"

    PID : Mapped[str] = mapped_column(String,primary_key=True ,index=True)
    PNAME : Mapped[String] = mapped_column(String)
    PPRICE : Mapped[Float] = mapped_column(Float)

class WareHouseDetails(Base):
    __tablename__ = "WareHouseDetails"

    WID : Mapped[String] = mapped_column(String,primary_key=True)
    LOCATION : Mapped[String] = mapped_column(String)

class ProductLocation(Base):
    __tablename__ = "ProductLocation"
    id : Mapped[Integer] = mapped_column(Integer,primary_key=True)
    WID : Mapped[String] = mapped_column(String)
    PID : Mapped[str] = mapped_column(String)
    PQUANTITY : Mapped[Integer] = mapped_column(Integer)


class OrderDetails(Base):

    __tablename__ = "OrderDetails"
    OID : Mapped[Integer] = mapped_column(Integer,primary_key=True,index=True)
    UID : Mapped[Integer] = mapped_column(Integer)
    PID : Mapped[Integer] = mapped_column(Integer)
    PNAME:Mapped[String] = mapped_column(String)
    PQUANTITY :Mapped[Integer] = mapped_column(Integer)
    PPRICE : Mapped[Float] = mapped_column(Float)
    WID : Mapped[Integer] = mapped_column(Integer)



class CartDetails(Base):

    __tablename__ = "CartDetails"
    ID : Mapped[Integer] = mapped_column(Integer,primary_key=True)
    UID : Mapped[str] = mapped_column(String)
    PID : Mapped[str] = mapped_column(String)
    PNAME:Mapped[String] = mapped_column(String)
    PQUANTITY :Mapped[Integer] = mapped_column(Integer)
    PPRICE : Mapped[Float] = mapped_column(Float)


class OrderRecord(Base):
    __tablename__ = "Orders"

    OID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UID: Mapped[str] = mapped_column(String, ForeignKey("UserDetails.UID"), index=True)
    WID: Mapped[str] = mapped_column(String, ForeignKey("WareHouseDetails.WID"))
    LOCATION: Mapped[str] = mapped_column(String)
    STATUS: Mapped[str] = mapped_column(String, default="placed")
    TOTAL_AMOUNT: Mapped[float] = mapped_column(Float)
    CREATED_AT: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class OrderItem(Base):
    __tablename__ = "OrderItems"

    ID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    OID: Mapped[int] = mapped_column(Integer, ForeignKey("Orders.OID"), index=True)
    PID: Mapped[str] = mapped_column(String, ForeignKey("ProductDetails.PID"))
    PNAME: Mapped[str] = mapped_column(String)
    PQUANTITY: Mapped[int] = mapped_column(Integer)
    PPRICE: Mapped[float] = mapped_column(Float)
    