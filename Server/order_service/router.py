from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    CartDetails,
    OrderItem,
    OrderRecord,
    ProductDetails,
    ProductLocation,
    UserDetails,
    WareHouseDetails,
)
from order_service.schemas import CheckoutRequest, CheckoutResponse

o_router = APIRouter()


# Checks out the customer's saved cart, reserves stock at one exact-location warehouse,
# records an order snapshot, and clears the cart in one database transaction.
@o_router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout_cart(
    checkout: CheckoutRequest,
    db: Session = Depends(get_db),
):
    user = db.get(UserDetails, checkout.UID)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    cart_stmt = (
        select(CartDetails)
        .where(CartDetails.UID == user.UID)
        .order_by(CartDetails.ID)
    )
    cart_rows = db.scalars(cart_stmt).all()
    if not cart_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The cart is empty",
        )

    requested_quantities: dict[str, int] = {}
    for cart_row in cart_rows:
        if cart_row.PQUANTITY <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cart quantity for product '{cart_row.PID}' must be positive",
            )
        requested_quantities[cart_row.PID] = (
            requested_quantities.get(cart_row.PID, 0) + cart_row.PQUANTITY
        )

    product_stmt = select(ProductDetails).where(
        ProductDetails.PID.in_(requested_quantities)
    )
    products = {product.PID: product for product in db.scalars(product_stmt).all()}
    missing_products = set(requested_quantities) - products.keys()
    if missing_products:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cart contains unavailable product IDs: {', '.join(sorted(missing_products))}",
        )

    warehouse_stmt = (
        select(WareHouseDetails)
        .where(WareHouseDetails.LOCATION == user.LOCATION)
        .order_by(WareHouseDetails.WID)
    )
    warehouses = db.scalars(warehouse_stmt).all()
    if not warehouses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No warehouse is available at the customer's location",
        )

    selected_warehouse: WareHouseDetails | None = None
    selected_stock: dict[str, list[ProductLocation]] = {}
    for warehouse in warehouses:
        stock_stmt = (
            select(ProductLocation)
            .where(
                ProductLocation.WID == warehouse.WID,
                ProductLocation.PID.in_(requested_quantities),
            )
            .order_by(ProductLocation.id)
        )
        stock_rows = db.scalars(stock_stmt).all()
        stock_by_product: dict[str, list[ProductLocation]] = {}
        for stock_row in stock_rows:
            stock_by_product.setdefault(stock_row.PID, []).append(stock_row)

        if all(
            sum(row.PQUANTITY for row in stock_by_product.get(product_id, []))
            >= requested_quantity
            for product_id, requested_quantity in requested_quantities.items()
        ):
            selected_warehouse = warehouse
            selected_stock = stock_by_product
            break

    if selected_warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No single warehouse at the customer's location has all requested quantities",
        )

    for product_id, requested_quantity in requested_quantities.items():
        remaining = requested_quantity
        for stock_row in selected_stock[product_id]:
            quantity_to_reserve = min(stock_row.PQUANTITY, remaining)
            if quantity_to_reserve <= 0:
                continue

            reserve_stmt = (
                update(ProductLocation)
                .where(
                    ProductLocation.id == stock_row.id,
                    ProductLocation.PQUANTITY >= quantity_to_reserve,
                )
                .values(
                    PQUANTITY=ProductLocation.PQUANTITY - quantity_to_reserve
                )
            )
            result = db.execute(reserve_stmt)
            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Inventory changed during checkout; please retry",
                )
            remaining -= quantity_to_reserve

        if remaining:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory changed during checkout; please retry",
            )

    order_items_data = [
        {
            "PID": product_id,
            "PNAME": products[product_id].PNAME,
            "PQUANTITY": requested_quantity,
            "PPRICE": products[product_id].PPRICE,
            "LINE_TOTAL": products[product_id].PPRICE * requested_quantity,
        }
        for product_id, requested_quantity in requested_quantities.items()
    ]
    total_amount = sum(item["LINE_TOTAL"] for item in order_items_data)
    order = OrderRecord(
        UID=user.UID,
        WID=selected_warehouse.WID,
        LOCATION=selected_warehouse.LOCATION,
        STATUS="placed",
        TOTAL_AMOUNT=total_amount,
    )
    db.add(order)

    try:
        db.flush()
        db.add_all(
            [
                OrderItem(
                    OID=order.OID,
                    PID=item["PID"],
                    PNAME=item["PNAME"],
                    PQUANTITY=item["PQUANTITY"],
                    PPRICE=item["PPRICE"],
                )
                for item in order_items_data
            ]
        )
        db.execute(
            delete(CartDetails).where(CartDetails.UID == user.UID)
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout could not be completed; please retry",
        ) from None

    db.refresh(order)
    return {
        "OID": order.OID,
        "UID": order.UID,
        "WID": order.WID,
        "LOCATION": order.LOCATION,
        "STATUS": order.STATUS,
        "TOTAL_AMOUNT": order.TOTAL_AMOUNT,
        "CREATED_AT": order.CREATED_AT,
        "ITEMS": order_items_data,
    }
