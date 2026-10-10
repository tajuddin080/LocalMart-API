from sqlalchemy import select

from database.models import UserDetails
from tests.support import ServiceTestCase
from user_service.router import u_router
from user_service.security import is_hashed_password, verify_password


class UserServiceTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mount_routers(u_router)

    def test_registration_hashes_password_and_creates_customer(self) -> None:
        response = self.client.post(
            "/adduser",
            json={
                "UID": "C1",
                "UEMAIL": "CUSTOMER@example.com",
                "UPWORD": "correct-horse",
                "LOCATION": " Town ",
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["ROLE"], "customer")
        self.assertEqual(body["LOCATION"], "Town")
        self.assertNotIn("UPWORD", body)

        with self.SessionLocal() as db:
            user = db.get(UserDetails, "C1")
            self.assertIsNotNone(user)
            self.assertEqual(user.UEMAIL, "customer@example.com")
            self.assertTrue(is_hashed_password(user.UPWORD))
            self.assertTrue(verify_password("correct-horse", user.UPWORD))

    def test_registration_rejects_client_selected_role(self) -> None:
        response = self.client.post(
            "/adduser",
            json={
                "UID": "C1",
                "UEMAIL": "customer@example.com",
                "UPWORD": "correct-horse",
                "ROLE": "admin",
                "LOCATION": "Town",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_registration_rejects_duplicate_id_or_email(self) -> None:
        self.add_customer()
        response = self.client.post(
            "/adduser",
            json={
                "UID": "C2",
                "UEMAIL": "customer@example.com",
                "UPWORD": "correct-horse",
                "LOCATION": "Town",
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_login_accepts_valid_password_and_rejects_invalid_password(self) -> None:
        self.client.post(
            "/adduser",
            json={
                "UID": "C1",
                "UEMAIL": "customer@example.com",
                "UPWORD": "correct-horse",
                "LOCATION": "Town",
            },
        )

        success = self.client.post(
            "/login",
            json={"Uemail": "customer@example.com", "Upword": "correct-horse"},
        )
        failure = self.client.post(
            "/login",
            json={"Uemail": "customer@example.com", "Upword": "wrong-password"},
        )

        self.assertEqual(success.status_code, 200)
        self.assertNotIn("UPWORD", success.json())
        self.assertEqual(failure.status_code, 401)

    def test_login_upgrades_legacy_plaintext_password(self) -> None:
        with self.SessionLocal() as db:
            db.add(
                UserDetails(
                    UID="C1",
                    UEMAIL="customer@example.com",
                    UPWORD="legacy-password",
                    ROLE="customer",
                    LOCATION="Town",
                )
            )
            db.commit()

        response = self.client.post(
            "/login",
            json={"Uemail": "customer@example.com", "Upword": "legacy-password"},
        )

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as db:
            user = db.scalars(
                select(UserDetails).where(UserDetails.UID == "C1")
            ).one()
            self.assertTrue(is_hashed_password(user.UPWORD))
            self.assertTrue(verify_password("legacy-password", user.UPWORD))

    def test_profile_update_changes_email_and_browsing_location(self) -> None:
        self.add_customer()
        response = self.client.put(
            "/update_user",
            json={
                "UID": "C1",
                "UEMAIL": "updated@example.com",
                "LOCATION": "New Town",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["UEMAIL"], "updated@example.com")
        self.assertEqual(response.json()["LOCATION"], "New Town")

    def test_profile_update_rejects_duplicate_email(self) -> None:
        self.add_customer()
        self.add_customer(uid="C2", email="other@example.com")
        response = self.client.put(
            "/update_user",
            json={
                "UID": "C2",
                "UEMAIL": "customer@example.com",
                "LOCATION": "Town",
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_delete_user_and_missing_user_response(self) -> None:
        self.add_customer()
        deleted = self.client.delete("/delete_user", params={"u_id": "C1"})
        missing = self.client.delete("/delete_user", params={"u_id": "C1"})

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(missing.status_code, 404)
