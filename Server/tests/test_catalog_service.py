from sqlalchemy import select

from catalog_service.router import c_router
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


class CatalogServiceTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mount_routers(c_router, o_router)
        self.add_customer()
        with self.SessionLocal() as db:
            db.add_all(
                [
                    ProductDetails(PID="P1", PNAME="Tea", PPRICE=2.5),
                    ProductDetails(PID="P2", PNAME="Rice", PPRICE=4.0),
                    WareHouseDetails(WID="W1", LOCATION="Town"),
                    ProductLocation(WID="W1", PID="P1", PQUANTITY=10),
                    ProductLocation(WID="W1", PID="P2", PQUANTITY=10),
                ]
            )
            db.commit()

    def test_cart_add_increments_existing_quantity_and_uses_current_price(self) -> None:
        first = self.client.post(
            "/cart/C1/items",
            json={"PID": "P1", "PQUANTITY": 2},
        )
        second = self.client.post(
            "/cart/C1/items",
            json={"PID": "P1", "PQUANTITY": 3},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["ITEMS"][0]["PNAME"], "Tea")
        self.assertEqual(second.json()["ITEMS"][0]["PQUANTITY"], 5)
        self.assertEqual(second.json()["ITEMS"][0]["PPRICE"], 2.5)
        self.assertEqual(second.json()["TOTAL_AMOUNT"], 12.5)
        with self.SessionLocal() as db:
            rows = db.scalars(
                select(CartDetails).where(
                    CartDetails.UID == "C1",
                    CartDetails.PID == "P1",
                )
            ).all()
            self.assertEqual(len(rows), 1)

    def test_cart_read_update_remove_and_clear(self) -> None:
        self.client.post("/cart/C1/items", json={"PID": "P1", "PQUANTITY": 2})
        self.client.post("/cart/C1/items", json={"PID": "P2", "PQUANTITY": 3})

        cart = self.client.get("/cart/C1")
        updated = self.client.put(
            "/cart/C1/items/P1",
            json={"PQUANTITY": 4},
        )
        removed = self.client.delete("/cart/C1/items/P2")
        cleared = self.client.delete("/cart/C1")
        empty_cart = self.client.get("/cart/C1")

        self.assertEqual(cart.status_code, 200)
        self.assertEqual(cart.json()["TOTAL_AMOUNT"], 17.0)
        self.assertEqual(updated.json()["ITEMS"][0]["PQUANTITY"], 4)
        self.assertEqual(updated.json()["TOTAL_AMOUNT"], 22.0)
        self.assertEqual(removed.json()["TOTAL_AMOUNT"], 10.0)
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(empty_cart.json()["ITEMS"], [])

    def test_cart_rejects_unknown_user_product_and_invalid_quantity(self) -> None:
        unknown_user = self.client.get("/cart/unknown")
        unknown_product = self.client.post(
            "/cart/C1/items",
            json={"PID": "missing", "PQUANTITY": 1},
        )
        invalid_quantity = self.client.post(
            "/cart/C1/items",
            json={"PID": "P1", "PQUANTITY": 0},
        )

        self.assertEqual(unknown_user.status_code, 404)
        self.assertEqual(unknown_product.status_code, 404)
        self.assertEqual(invalid_quantity.status_code, 422)

    def test_order_history_and_details_are_scoped_to_customer(self) -> None:
        self.client.post("/cart/C1/items", json={"PID": "P1", "PQUANTITY": 2})
        checkout = self.client.post("/checkout", json={"UID": "C1"})
        self.assertEqual(checkout.status_code, 201, checkout.text)
        order_id = checkout.json()["OID"]

        history = self.client.get("/orders/C1")
        details = self.client.get(f"/orders/C1/{order_id}")
        wrong_owner = self.client.get(f"/orders/C2/{order_id}")
        invalid_pagination = self.client.get("/orders/C1?limit=101")

        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 1)
        self.assertEqual(history.json()[0]["ITEMS"][0]["PNAME"], "Tea")
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()["OID"], order_id)
        self.assertEqual(wrong_owner.status_code, 404)
        self.assertEqual(invalid_pagination.status_code, 422)

        with self.SessionLocal() as db:
            self.assertEqual(len(db.scalars(select(OrderRecord)).all()), 1)
            self.assertEqual(len(db.scalars(select(OrderItem)).all()), 1)
