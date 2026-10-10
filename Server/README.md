# LocalMart API

LocalMart API is a FastAPI backend for an online mart where customers browse products stocked at warehouses in their profile location, add items to a cart, and place orders.

## Services

- **User Service** — customer registration, login, and profile management, with hashed passwords.
- **Warehouse Service** — warehouse and inventory management, including stock scoped to each warehouse.
- **Order Service** — checkout from a customer’s cart, inventory deduction, and order creation. Each order is fulfilled by one warehouse at the customer’s exact profile location.
- **Catalog Service** — cart operations and customer order history.

## Run locally

Requires Python 3.13 or later. From the project root, start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Interactive API documentation is available at:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

The SQLite database is configured at `database/central.db`, relative to the working directory.

## Frontend integration

The responsive LocalMart storefront is available at <http://127.0.0.1:8000/app>
when the API is running alongside the `client` folder. See [docs/API.md](docs/API.md)
for the endpoint reference, request and response examples, HTTP errors, and a
recommended customer shopping flow.

## Current limitations

This project is under active development. Authentication tokens and authorization are not yet implemented. Several endpoints accept a user ID in the URL or request body, but this only identifies a record; it does not securely authenticate the caller or prevent access to another user's operations. Do not expose this API to untrusted users or use it in production until authentication and authorization are added.

Warehouse and checkout selection currently use an exact location string match, not geographic distance. Checkout requires a single warehouse at that location to fulfill the entire cart. Database `create_all()` creates missing tables but does not migrate existing schemas.
