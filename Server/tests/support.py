import unittest
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import get_db
from database.models import Base, UserDetails


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.engine = engine
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )
        self.app = FastAPI()

        def override_get_db() -> Iterator[Any]:
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client: TestClient

    def mount_routers(self, *routers: Any) -> None:
        for router in routers:
            self.app.include_router(router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        if hasattr(self, "client"):
            self.client.close()
        self.engine.dispose()

    def add_customer(
        self,
        uid: str = "C1",
        email: str = "customer@example.com",
        location: str = "Town",
    ) -> None:
        with self.SessionLocal() as db:
            db.add(
                UserDetails(
                    UID=uid,
                    UEMAIL=email,
                    UPWORD="test-password-hash",
                    ROLE="customer",
                    LOCATION=location,
                )
            )
            db.commit()
