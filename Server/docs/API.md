# LocalMart API Guide

This guide describes the API currently implemented by the backend and is intended for frontend integration.

## Base URL and interactive docs

When running locally, use:

```text
http://127.0.0.1:8000
```

All routes are mounted at the root; there are no `/users`, `/warehouse`, or `/catalog` prefixes.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

The examples below use `fetch` and assume the frontend and API are reachable from the same origin. If they run on different origins, configure CORS on the API before browser requests.

## Important behavior and limitations

- User IDs in request paths and checkout bodies are identifiers only, **not authentication**. There are no access tokens or authorization checks yet. A caller may be able to access another user's cart, profile operations, checkout, or order history by changing a UID. This API must not be exposed to untrusted users until authentication and ownership enforcement are implemented.
- Public registration always creates a `customer`; the client cannot choose a role. Admin accounts must be provisioned separately.
- Passwords are hashed on registration. Successful login upgrades an existing plaintext password to a hash. Passwords are never returned by the API.
- Customer and warehouse locations are plain text. Inventory browsing and checkout require an exact match between the customer's location and a warehouse's location. This is not nearest-warehouse calculation.
- Checkout requires one matching warehouse to fulfill the entire cart. It will not split an order across warehouses.
- Product name and price are shared product data. Inventory quantity belongs to a warehouse.
- Checkout uses current product names and prices at the time of checkout; the cart's stored name and price are not authoritative.
- The database is SQLite at `database/central.db`, relative to the application's working directory. `Base.metadata.create_all()` creates missing tables but does not migrate existing table schemas.
- Warehouse write endpoints are not currently protected by admin-role or assigned-warehouse authorization.

## Common response and error handling

Successful responses are JSON. Errors generally use FastAPI's standard shape:

```json
{
  "detail": "Human-readable error description"
}
```

Common statuses:

| Status | Meaning |
| --- | --- |
| `200` | Request succeeded |
| `201` | Resource created |
| `401` | Login credentials are invalid |
| `404` | User, product, warehouse, inventory entry, or order was not found |
| `409` | Duplicate/conflicting data or checkout cannot be fulfilled |
| `422` | Request validation failed |

For `422`, FastAPI may return a `detail` array containing field-level validation errors rather than a string.

## Endpoint reference

### Root

#### `GET /`

Returns a simple API welcome message.

Example response:

```json
{"message": "Welcome to the Store API Dashboard"}
```

### User Service

#### `POST /adduser`

Creates a customer account. Role is set by the server to `customer`.

Request:

```json
{
  "UID": "C101",
  "UEMAIL": "customer@example.com",
  "UPWORD": "correct-horse-123",
  "LOCATION": "Jubilee Hills"
}
```

`UID` is 1–50 characters, `UPWORD` is 8–128 characters, and `LOCATION` is 1–100 characters. Email must be valid. Surrounding whitespace is trimmed from UID and location; email is normalized to lowercase.

Response (`201`):

```json
{
  "UID": "C101",
  "UEMAIL": "customer@example.com",
  "ROLE": "customer",
  "LOCATION": "Jubilee Hills"
}
```

Duplicate user ID or email returns `409`. Extra fields such as `ROLE` are rejected with `422`.

#### `POST /login`

Verifies email and password. This endpoint does **not** issue an access token or establish a session.

Request:

```json
{
  "Uemail": "customer@example.com",
  "Upword": "correct-horse-123"
}
```

Response (`200`) has the same fields as the account response above and never includes the password. Invalid credentials return `401`.

#### `PUT /update_user`

Updates the account email and browsing location. Password and role are not changed by this endpoint.

Request:

```json
{
  "UID": "C101",
  "UEMAIL": "new-address@example.com",
  "LOCATION": "Madhapur"
}
```

Response (`200`) is the updated user response. Missing UID returns `404`; an email already in use returns `409`.

#### `DELETE /delete_user?u_id=C101`

Deletes the account identified by the `u_id` query parameter.

Response (`200`):

```json
{"message": "User deleted"}
```

Missing user returns `404`. This destructive endpoint currently has no authentication/authorization.

#### `GET /greeting`

Simple service greeting. Example response: `"Hello"`.

### Warehouse Service

#### `GET /warehouses`

Lists warehouses, optionally filtered by exact location:

```text
GET /warehouses?location=Jubilee%20Hills
```

Returns a JSON array of warehouse records:

```json
[
  {"WID": "W209", "LOCATION": "Jubilee Hills"}
]
```

#### `POST /addwarehouse`

Creates one or more warehouses. Body must be a non-empty array.

```json
[
  {"WID": "W209", "LOCATION": "Jubilee Hills"}
]
```

Response (`201`):

```json
{"message": "Warehouses added", "warehouses_added": 1}
```

Duplicate warehouse IDs return `409`.

#### `PUT /updatewarehouse`

Updates the location of an existing warehouse. `WID` identifies the row and cannot be changed by this endpoint.

Request:

```json
{"WID": "W209", "LOCATION": "Madhapur"}
```

Response (`200`) contains the updated warehouse fields. Missing warehouse returns `404`.

#### `DELETE /deletewarehouse?w_id=W209`

Deletes the warehouse and its inventory records; shared product records remain.

Response (`200`):

```json
{"message": "Warehouse and its inventory records deleted"}
```

Missing warehouse returns `404`.

#### `GET /product?Location=Jubilee%20Hills`

Lists products stocked in warehouses at the exact requested location. A product stocked at multiple warehouses in that location can appear more than once, with a warehouse ID and quantity for each record.

Example response:

```json
[
  {
    "PID": "P101",
    "PNAME": "Wireless Mouse",
    "PPRICE": 799.0,
    "PQUANTITY": 10,
    "WID": "W209"
  }
]
```

No matching inventory returns an empty array.

#### `POST /addproduct`

Adds products and warehouse stock. Body must be a non-empty array. For an existing product ID, submitted name and price must match its shared product details; only a new warehouse-specific stock record is created.

```json
[
  {
    "PID": "P101",
    "PNAME": "Wireless Mouse",
    "PPRICE": 799.0,
    "PQUANTITY": 10,
    "WID": "W209"
  }
]
```

`PID` must start with `P`; price and quantity must be non-negative. The warehouse must already exist. Success returns `201`:

```json
{"message": "Inventory records added", "records_added": 1}
```

Missing warehouse returns `404`; duplicate inventory or conflicting product details return `409`.

#### `PUT /updateproduct`

Replaces the quantity for one existing product/warehouse inventory record.

```json
{"PID": "P101", "WID": "W209", "PQUANTITY": 8}
```

Response (`200`):

```json
{
  "message": "Warehouse stock updated",
  "PID": "P101",
  "WID": "W209",
  "PQUANTITY": 8
}
```

Quantity must be non-negative. Missing inventory record returns `404`.

#### `DELETE /deleteproduct?p_id=P101&w_id=W209`

Removes the product's stock record from the specified warehouse only. It does not delete the shared product.

Response (`200`):

```json
{"message": "Product removed from warehouse inventory"}
```

Missing inventory record returns `404`.

### Catalog Service

#### `GET /cart/{uid}`

Gets a customer's cart, recalculating product names, prices, line totals, and cart total from current product records.

Example response:

```json
{
  "UID": "C101",
  "LOCATION": "Jubilee Hills",
  "ITEMS": [
    {
      "PID": "P101",
      "PNAME": "Wireless Mouse",
      "PQUANTITY": 2,
      "PPRICE": 799.0,
      "LINE_TOTAL": 1598.0
    }
  ],
  "TOTAL_AMOUNT": 1598.0
}
```

An empty cart returns the same shape with an empty `ITEMS` array and `TOTAL_AMOUNT` of `0`. Missing user returns `404`.

#### `POST /cart/{uid}/items`

Adds a product to the cart. Re-adding a product increments its existing quantity.

Request:

```json
{"PID": "P101", "PQUANTITY": 2}
```

Response (`200`) is the complete cart response. Quantity must be greater than zero. Missing user or product returns `404`.

#### `PUT /cart/{uid}/items/{pid}`

Sets the cart quantity for one existing item:

```json
{"PQUANTITY": 3}
```

Response (`200`) is the complete updated cart. Quantity must be greater than zero. Missing user or item returns `404`.

#### `DELETE /cart/{uid}/items/{pid}`

Removes a product from the cart and returns the remaining cart (`200`). If the product was not present, deletion leaves the cart unchanged.

#### `DELETE /cart/{uid}`

Clears all items from the cart.

Response (`200`):

```json
{"message": "Cart cleared"}
```

### Order Service

#### `POST /checkout`

Checks out all items in the saved cart. The customer location must exactly match a warehouse location, and one such warehouse must have the requested quantities for every cart product. The backend calculates prices from current product data, records an order snapshot, decrements stock, and clears the cart only when the transaction succeeds.

Request:

```json
{"UID": "C101"}
```

Success (`201`) response:

```json
{
  "OID": 1,
  "UID": "C101",
  "WID": "W209",
  "LOCATION": "Jubilee Hills",
  "STATUS": "placed",
  "TOTAL_AMOUNT": 1598.0,
  "CREATED_AT": "2026-10-10T07:30:00",
  "ITEMS": [
    {
      "PID": "P101",
      "PNAME": "Wireless Mouse",
      "PQUANTITY": 2,
      "PPRICE": 799.0,
      "LINE_TOTAL": 1598.0
    }
  ]
}
```

Empty cart returns `400`; missing user returns `404`; no matching warehouse or insufficient stock returns `409`. On failure, checkout does not clear the cart or commit stock changes.

### Order history

#### `GET /orders/{uid}?limit=20&offset=0`

Lists the user's orders, newest first, with saved order items. `limit` must be 1–100; `offset` must be zero or greater. A user with no orders receives `[]`.

#### `GET /orders/{uid}/{oid}`

Returns one order and its saved items only if the order belongs to the requested UID. Missing order or an order owned by another UID returns `404`.

## Recommended website flow

1. Register using `POST /adduser`, then store the returned `UID` for the current frontend flow.
2. Log in with `POST /login`. At present, this verifies credentials but does not create a token/session.
3. Load available locations with `GET /warehouses`; collect a location matching an existing warehouse.
4. Load local stock with `GET /product?Location=...`. Display `PID`, `PNAME`, `PPRICE`, `PQUANTITY`, and `WID`; only show products with positive stock.
5. Load the cart with `GET /cart/{uid}`.
6. Add, update, or remove items with the cart endpoints. Display the returned `TOTAL_AMOUNT`.
7. Place the order with `POST /checkout` using the UID. Show the returned order summary on success. If checkout returns `409`, keep the cart view and tell the customer that location/availability must be checked.
8. Show history with `GET /orders/{uid}` and a selected order with `GET /orders/{uid}/{oid}`.

Do not treat a UID saved in browser storage as secure identity. When authentication is implemented, derive the user from the verified token instead of accepting a caller-chosen UID.

## Example frontend helper

```javascript
const API_BASE = "http://127.0.0.1:8000";

async function apiRequest(path, options = {}) {
  const { headers = {}, ...requestOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return body;
}

const cart = await apiRequest("/cart/C101");
```

The helper throws on HTTP errors so the UI can show an error state rather than treating a failed request as a successful response.
