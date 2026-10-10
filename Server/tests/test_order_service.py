from sqlalchemy import select

from database.models import (
    CartDetails,
    OrderItem,
    OrderRecord,
    ProductDetails,
    ProductLocation,
    WareHouseDetails,
)
from order_service.router import o_router
from tests.support import ServiceTestCase


class OrderServiceTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mount_routers(o_router)
        self.add_customer()

    def seed_order_inventory(self) -> None:
        with self.SessionLocal() as db:
            db.add_all(
                [
                    WareHouseDetails(WID="W1", LOCATION="Town"),
                    WareHouseDetails(WID="W2", LOCATION="Town"),
                    ProductDetails(PID="P1", PNAME="Tea", PPRICE=2.5),
                    ProductDetails(PID="P2", PNAME="Rice", PPRICE=4.0),
                    ProductLocation(WID="W1", PID="P1", PQUANTITY=5),
                    ProductLocation(WID="W1", PID="P2", PQUANTITY=1),
                    ProductLocation(WID="W2", PID="P1", PQUANTITY=2),
                    ProductLocation(WID="W2", PID="P2", PQUANTITY=4),
                    CartDetails(
                        UID="C1",
                        PID="P1",
                        PNAME="stale name",
                        PQUANTITY=2,
                        PPRICE=99.0,
                    ),
                    CartDetails(
                        UID="C1",
                        PID="P2",
                        PNAME="Rice",
                        PQUANTITY=3,
                        PPRICE=4.0,
                    ),
                ]
            )
            db.commit()

    def test_checkout_selects_one_fulfilling_warehouse_and_records_order(self) -> None:
        self.seed_order_inventory()

        response = self.client.post("/checkout", json={"UID": "C1"})

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["WID"], "W2")
        self.assertEqual(body["TOTAL_AMOUNT"], 17.0)
        self.assertEqual(
            {item["PID"]: item["PNAME"] for item in body["ITEMS"]},
            {"P1": "Tea", "P2": "Rice"},
        )
        with self.SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    select(ProductLocation.PQUANTITY).where(
                        ProductLocation.WID == "W2",
                        ProductLocation.PID == "P1",
                    )
                ),
                0,
            )
            self.assertEqual(
                db.scalar(
                    select(ProductLocation.PQUANTITY).where(
                        ProductLocation.WID == "W2",
                        ProductLocation.PID == "P2",
                    )
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(ProductLocation.PQUANTITY).where(
                        ProductLocation.WID == "W1",
                        ProductLocation.PID == "P1",
                    )
                ),
                5,
            )
            self.assertEqual(len(db.scalars(select(OrderRecord)).all()), 1)
            self.assertEqual(len(db.scalars(select(OrderItem)).all()), 2)
            self.assertEqual(
                db.scalars(select(CartDetails).where(CartDetails.UID == "C1")).all(),
                [],
            )

    def test_failed_checkout_preserves_cart_stock_and_order_history(self) -> None:
        self.seed_order_inventory()
        with self.SessionLocal() as db:
            cart_item = db.scalars(
                select(CartDetails).where(
                    CartDetails.UID == "C1",
                    CartDetails.PID == "P1",
                )
            ).one()
            cart_item.PQUANTITY = 20
            db.commit()

        response = self.client.post("/checkout", json={"UID": "C1"})

        self.assertEqual(response.status_code, 409)
        with self.SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    select(ProductLocation.PQUANTITY).where(
                        ProductLocation.WID == "W1",
                        ProductLocation.PID == "P1",
                    )
                ),
                5,
            )
            self.assertEqual(
                db.scalar(
                    select(ProductLocation.PQUANTITY).where(
                        ProductLocation.WID == "W2",
                        ProductLocation.PID == "P1",
                    )
                ),
                2,
            )
            self.assertEqual(len(db.scalars(select(OrderRecord)).all()), 0)
            self.assertEqual(
                len(db.scalars(select(CartDetails).where(CartDetails.UID == "C1")).all()),
                2,
            )

    def test_checkout_rejects_empty_cart_and_unknown_customer(self) -> None:
        empty_cart = self.client.post("/checkout", json={"UID": "C1"})
        unknown_customer = self.client.post("/checkout", json={"UID": "unknown"})

        self.assertEqual(empty_cart.status_code, 400)
        self.assertEqual(unknown_customer.status_code, 404)
