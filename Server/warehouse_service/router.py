from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import ProductDetails, ProductLocation, WareHouseDetails
from warehouse_service.schemas import ProductStockCreate, ProductStockUpdate, WareHouse

w_router = APIRouter()


# Lists product details and stock for every warehouse matching the exact location.
@w_router.get("/product")
def get_inventory_details_optimized(
    Location: str = Query(min_length=1),
    db: Session = Depends(get_db),
):
    location = Location.strip()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location must not be blank",
        )

    stmt = (
        select(
            ProductDetails.PID,
            ProductDetails.PNAME,
            ProductDetails.PPRICE,
            ProductLocation.PQUANTITY,
            WareHouseDetails.WID,
        )
        .join(ProductLocation, ProductDetails.PID == ProductLocation.PID)
        .join(WareHouseDetails, WareHouseDetails.WID == ProductLocation.WID)
        .where(WareHouseDetails.LOCATION == location)
        .order_by(WareHouseDetails.WID, ProductDetails.PID)
    )
    return db.execute(stmt).mappings().all()


# Adds shared product details when needed and creates warehouse-specific stock records.
@w_router.post("/addproduct", status_code=status.HTTP_201_CREATED)
def add_product_details(
    p_data: list[ProductStockCreate] = Body(min_length=1),
    db: Session = Depends(get_db),
):
    products_in_batch: dict[str, tuple[str, float]] = {}
    stock_entries_in_batch: set[tuple[str, str]] = set()
    products_added = 0

    for product in p_data:
        warehouse = db.get(WareHouseDetails, product.WID)
        if warehouse is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse '{product.WID}' not found",
            )

        product_details = db.get(ProductDetails, product.PID)
        batch_details = products_in_batch.get(product.PID)
        if product_details is None and batch_details is None:
            products_in_batch[product.PID] = (product.PNAME, product.PPRICE)
        elif product_details is not None and (
            product_details.PNAME != product.PNAME
            or product_details.PPRICE != product.PPRICE
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{product.PID}' already exists with different shared details",
            )
        elif batch_details is not None and batch_details != (
            product.PNAME,
            product.PPRICE,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{product.PID}' has conflicting details in this request",
            )

        stock_key = (product.PID, product.WID)
        if stock_key in stock_entries_in_batch:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{product.PID}' is repeated for warehouse '{product.WID}'",
            )
        stock_entries_in_batch.add(stock_key)

        existing_stock_stmt = select(ProductLocation.id).where(
            ProductLocation.PID == product.PID,
            ProductLocation.WID == product.WID,
        )
        if db.scalar(existing_stock_stmt) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{product.PID}' already has an inventory record in warehouse '{product.WID}'",
            )

        if product_details is None and batch_details is None:
            db.add(
                ProductDetails(
                    PID=product.PID,
                    PNAME=product.PNAME,
                    PPRICE=product.PPRICE,
                )
            )
        db.add(
            ProductLocation(
                PID=product.PID,
                WID=product.WID,
                PQUANTITY=product.PQUANTITY,
            )
        )
        products_added += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The product or inventory record already exists",
        ) from None

    return {"message": "Inventory records added", "records_added": products_added}


# Replaces the stock quantity for one product in one warehouse.
@w_router.put("/updateproduct")
def update_product_details(
    updated_product: ProductStockUpdate,
    db: Session = Depends(get_db),
):
    stmt = select(ProductLocation).where(
        ProductLocation.PID == updated_product.PID,
        ProductLocation.WID == updated_product.WID,
    )
    stock = db.scalars(stmt).first()
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product inventory record not found for this warehouse",
        )

    stock.PQUANTITY = updated_product.PQUANTITY
    db.commit()
    db.refresh(stock)
    return {
        "message": "Warehouse stock updated",
        "PID": stock.PID,
        "WID": stock.WID,
        "PQUANTITY": stock.PQUANTITY,
    }


# Removes a product's stock record from one warehouse without deleting the shared product.
@w_router.delete("/deleteproduct")
def delete_product_details(p_id: str, w_id: str, db: Session = Depends(get_db)):
    stmt = select(ProductLocation).where(
        ProductLocation.PID == p_id.strip(),
        ProductLocation.WID == w_id.strip(),
    )
    stock = db.scalars(stmt).first()
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product inventory record not found for this warehouse",
        )

    db.delete(stock)
    db.commit()
    return {"message": "Product removed from warehouse inventory"}


# Lists all warehouses, or only warehouses whose location exactly matches the optional filter.
@w_router.get("/warehouses")
def get_warehouses(
    location: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    stmt = select(WareHouseDetails)
    if location is not None:
        normalized_location = location.strip()
        if not normalized_location:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Location must not be blank",
            )
        stmt = stmt.where(WareHouseDetails.LOCATION == normalized_location)
    return db.scalars(stmt.order_by(WareHouseDetails.WID)).all()


# Creates warehouse records after checking for duplicate warehouse IDs.
@w_router.post("/addwarehouse", status_code=status.HTTP_201_CREATED)
def add_warehouse_details(
    w_details: list[WareHouse] = Body(min_length=1),
    db: Session = Depends(get_db),
):
    warehouse_ids: set[str] = set()
    for warehouse in w_details:
        if warehouse.WID in warehouse_ids or db.get(WareHouseDetails, warehouse.WID):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warehouse '{warehouse.WID}' already exists",
            )
        warehouse_ids.add(warehouse.WID)

    db.add_all(
        [
            WareHouseDetails(WID=warehouse.WID, LOCATION=warehouse.LOCATION)
            for warehouse in w_details
        ]
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more warehouse IDs already exist",
        ) from None

    return {"message": "Warehouses added", "warehouses_added": len(w_details)}


# Changes the location stored for an existing warehouse.
@w_router.put("/updatewarehouse")
def update_warehouse_details(w_data: WareHouse, db: Session = Depends(get_db)):
    warehouse = db.get(WareHouseDetails, w_data.WID)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    warehouse.LOCATION = w_data.LOCATION
    db.commit()
    db.refresh(warehouse)
    return warehouse


# Deletes a warehouse and its inventory records, but leaves shared product details intact.
@w_router.delete("/deletewarehouse")
def delete_warehouse_details(w_id: str, db: Session = Depends(get_db)):
    warehouse = db.get(WareHouseDetails, w_id.strip())
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    db.execute(delete(ProductLocation).where(ProductLocation.WID == warehouse.WID))
    db.delete(warehouse)
    db.commit()
    return {"message": "Warehouse and its inventory records deleted"}
