from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from catalog_service.schemas import (
    CartItemAdd,
    CartItemQuantityUpdate,
    CartResponse,
    OrderResponse,
)
from database.connection import get_db
from database.models import (
    CartDetails,
    OrderItem,
    OrderRecord,
    ProductDetails,
    UserDetails,
)

c_router = APIRouter()


def _require_user(db: Session, uid: str) -> UserDetails:
    user = db.get(UserDetails, uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _get_cart_response(db: Session, user: UserDetails) -> dict[str, object]:
    cart_stmt = (
        select(CartDetails)
        .where(CartDetails.UID == user.UID)
        .order_by(CartDetails.ID)
    )
    cart_rows = db.scalars(cart_stmt).all()
    quantities: dict[str, int] = {}
    for row in cart_rows:
        quantities[row.PID] = quantities.get(row.PID, 0) + row.PQUANTITY

    products_stmt = select(ProductDetails).where(ProductDetails.PID.in_(quantities))
    products = {product.PID: product for product in db.scalars(products_stmt).all()}
    missing_products = set(quantities) - products.keys()
    if missing_products:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cart contains unavailable product IDs: {', '.join(sorted(missing_products))}",
        )

    items = [
        {
            "PID": pid,
            "PNAME": products[pid].PNAME,
            "PQUANTITY": quantity,
            "PPRICE": products[pid].PPRICE,
            "LINE_TOTAL": products[pid].PPRICE * quantity,
        }
        for pid, quantity in sorted(quantities.items())
    ]
    return {
        "UID": user.UID,
        "LOCATION": user.LOCATION,
        "ITEMS": items,
        "TOTAL_AMOUNT": sum(item["LINE_TOTAL"] for item in items),
    }


def _get_order_response(
    order: OrderRecord,
    items: list[OrderItem],
) -> dict[str, object]:
    return {
        "OID": order.OID,
        "UID": order.UID,
        "WID": order.WID,
        "LOCATION": order.LOCATION,
        "STATUS": order.STATUS,
        "TOTAL_AMOUNT": order.TOTAL_AMOUNT,
        "CREATED_AT": order.CREATED_AT,
        "ITEMS": [
            {
                "PID": item.PID,
                "PNAME": item.PNAME,
                "PQUANTITY": item.PQUANTITY,
                "PPRICE": item.PPRICE,
                "LINE_TOTAL": item.PPRICE * item.PQUANTITY,
            }
            for item in items
        ],
    }


# Returns the customer's cart using current product names and prices.
@c_router.get("/cart/{uid}", response_model=CartResponse)
def get_cart(uid: str, db: Session = Depends(get_db)):
    user = _require_user(db, uid)
    return _get_cart_response(db, user)


# Adds the requested quantity to the customer's existing cart quantity for that product.
@c_router.post(
    "/cart/{uid}/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
)
def add_cart_item(
    uid: str,
    item: CartItemAdd,
    db: Session = Depends(get_db),
):
    user = _require_user(db, uid)
    product = db.get(ProductDetails, item.PID)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing_stmt = (
        select(CartDetails)
        .where(CartDetails.UID == user.UID, CartDetails.PID == product.PID)
        .order_by(CartDetails.ID)
    )
    existing_rows = db.scalars(existing_stmt).all()
    if existing_rows:
        existing_rows[0].PQUANTITY = (
            sum(row.PQUANTITY for row in existing_rows) + item.PQUANTITY
        )
        for duplicate_row in existing_rows[1:]:
            db.delete(duplicate_row)
    else:
        db.add(
            CartDetails(
                UID=user.UID,
                PID=product.PID,
                PNAME=product.PNAME,
                PQUANTITY=item.PQUANTITY,
                PPRICE=product.PPRICE,
            )
        )

    db.commit()
    return _get_cart_response(db, user)


# Sets the customer's cart quantity for one product to the submitted quantity.
@c_router.put(
    "/cart/{uid}/items/{pid}",
    response_model=CartResponse,
)
def update_cart_item(
    uid: str,
    pid: str,
    quantity_update: CartItemQuantityUpdate,
    db: Session = Depends(get_db),
):
    user = _require_user(db, uid)
    existing_stmt = (
        select(CartDetails)
        .where(CartDetails.UID == user.UID, CartDetails.PID == pid)
        .order_by(CartDetails.ID)
    )
    existing_rows = db.scalars(existing_stmt).all()
    if not existing_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product is not in this cart",
        )

    existing_rows[0].PQUANTITY = quantity_update.PQUANTITY
    for duplicate_row in existing_rows[1:]:
        db.delete(duplicate_row)
    db.commit()
    return _get_cart_response(db, user)


# Removes one product from the customer's cart.
@c_router.delete("/cart/{uid}/items/{pid}", response_model=CartResponse)
def remove_cart_item(uid: str, pid: str, db: Session = Depends(get_db)):
    user = _require_user(db, uid)
    db.execute(
        delete(CartDetails).where(
            CartDetails.UID == user.UID,
            CartDetails.PID == pid,
        )
    )
    db.commit()
    return _get_cart_response(db, user)


# Removes all items from the customer's cart.
@c_router.delete("/cart/{uid}", status_code=status.HTTP_200_OK)
def clear_cart(uid: str, db: Session = Depends(get_db)):
    user = _require_user(db, uid)
    db.execute(delete(CartDetails).where(CartDetails.UID == user.UID))
    db.commit()
    return {"message": "Cart cleared"}


# Lists a customer's orders, newest first, with each order's saved item details.
@c_router.get("/orders/{uid}", response_model=list[OrderResponse])
def get_order_history(
    uid: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    user = _require_user(db, uid)
    orders_stmt = (
        select(OrderRecord)
        .where(OrderRecord.UID == user.UID)
        .order_by(OrderRecord.CREATED_AT.desc(), OrderRecord.OID.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = db.scalars(orders_stmt).all()
    if not orders:
        return []

    order_ids = [order.OID for order in orders]
    items_stmt = (
        select(OrderItem)
        .where(OrderItem.OID.in_(order_ids))
        .order_by(OrderItem.ID)
    )
    items_by_order: dict[int, list[OrderItem]] = {}
    for item in db.scalars(items_stmt).all():
        items_by_order.setdefault(item.OID, []).append(item)

    return [
        _get_order_response(order, items_by_order.get(order.OID, []))
        for order in orders
    ]


# Returns one order only when it belongs to the requested customer.
@c_router.get("/orders/{uid}/{oid}", response_model=OrderResponse)
def get_order_details(uid: str, oid: int, db: Session = Depends(get_db)):
    user = _require_user(db, uid)
    order_stmt = select(OrderRecord).where(
        OrderRecord.OID == oid,
        OrderRecord.UID == user.UID,
    )
    order = db.scalars(order_stmt).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    items_stmt = (
        select(OrderItem)
        .where(OrderItem.OID == order.OID)
        .order_by(OrderItem.ID)
    )
    items = db.scalars(items_stmt).all()
    return _get_order_response(order, items)
