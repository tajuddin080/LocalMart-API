from sqlalchemy import select

from database.models import ProductDetails, ProductLocation, WareHouseDetails
from tests.support import ServiceTestCase
from warehouse_service.router import w_router


class WarehouseServiceTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mount_routers(w_router)

    def test_create_and_filter_warehouses_by_exact_location(self) -> None:
        response = self.client.post(
            "/addwarehouse",
            json=[
                {"WID": "W1", "LOCATION": "Town"},
                {"WID": "W2", "LOCATION": "Other Town"},
            ],
        )

        self.assertEqual(response.status_code, 201)
        filtered = self.client.get("/warehouses", params={"location": "Town"})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([row["WID"] for row in filtered.json()], ["W1"])

    def test_warehouse_creation_rejects_duplicate_id(self) -> None:
        self.client.post(
            "/addwarehouse",
            json=[{"WID": "W1", "LOCATION": "Town"}],
        )
        response = self.client.post(
            "/addwarehouse",
            json=[{"WID": "W1", "LOCATION": "Town"}],
        )
        self.assertEqual(response.status_code, 409)

    def test_product_stock_can_be_added_to_multiple_warehouses(self) -> None:
        self.client.post(
            "/addwarehouse",
            json=[
                {"WID": "W1", "LOCATION": "Town"},
                {"WID": "W2", "LOCATION": "Town"},
            ],
        )

        response = self.client.post(
            "/addproduct",
            json=[
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 5,
                    "WID": "W1",
                },
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 8,
                    "WID": "W2",
                },
            ],
        )

        self.assertEqual(response.status_code, 201)
        inventory = self.client.get("/product", params={"Location": "Town"})
        self.assertEqual(inventory.status_code, 200)
        self.assertEqual(
            {row["WID"]: row["PQUANTITY"] for row in inventory.json()},
            {"W1": 5, "W2": 8},
        )

    def test_product_stock_rejects_missing_warehouse_and_duplicate_entry(self) -> None:
        missing_warehouse = self.client.post(
            "/addproduct",
            json=[
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 5,
                    "WID": "missing",
                }
            ],
        )
        self.assertEqual(missing_warehouse.status_code, 404)

        self.client.post(
            "/addwarehouse",
            json=[{"WID": "W1", "LOCATION": "Town"}],
        )
        duplicate = self.client.post(
            "/addproduct",
            json=[
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 5,
                    "WID": "W1",
                },
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 7,
                    "WID": "W1",
                },
            ],
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_stock_update_and_removal_are_warehouse_scoped(self) -> None:
        self.client.post(
            "/addwarehouse",
            json=[
                {"WID": "W1", "LOCATION": "Town"},
                {"WID": "W2", "LOCATION": "Town"},
            ],
        )
        self.client.post(
            "/addproduct",
            json=[
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 5,
                    "WID": "W1",
                },
                {
                    "PID": "P1",
                    "PNAME": "Tea",
                    "PPRICE": 2.5,
                    "PQUANTITY": 8,
                    "WID": "W2",
                },
            ],
        )

        update_response = self.client.put(
            "/updateproduct",
            json={"PID": "P1", "WID": "W1", "PQUANTITY": 3},
        )
        delete_response = self.client.delete(
            "/deleteproduct",
            params={"p_id": "P1", "w_id": "W1"},
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["PQUANTITY"], 3)
        self.assertEqual(delete_response.status_code, 200)
        with self.SessionLocal() as db:
            self.assertIsNotNone(db.get(ProductDetails, "P1"))
            remaining_stock = db.scalars(
                select(ProductLocation).where(ProductLocation.PID == "P1")
            ).all()
            self.assertEqual(len(remaining_stock), 1)
            self.assertEqual(remaining_stock[0].WID, "W2")
            self.assertEqual(remaining_stock[0].PQUANTITY, 8)

    def test_delete_warehouse_removes_its_stock(self) -> None:
        with self.SessionLocal() as db:
            db.add_all(
                [
                    WareHouseDetails(WID="W1", LOCATION="Town"),
                    ProductDetails(PID="P1", PNAME="Tea", PPRICE=2.5),
                    ProductLocation(WID="W1", PID="P1", PQUANTITY=5),
                ]
            )
            db.commit()

        response = self.client.delete("/deletewarehouse", params={"w_id": "W1"})

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as db:
            self.assertIsNone(db.get(WareHouseDetails, "W1"))
            self.assertIsNotNone(db.get(ProductDetails, "P1"))
            self.assertEqual(
                db.scalars(select(ProductLocation)).all(),
                [],
            )
