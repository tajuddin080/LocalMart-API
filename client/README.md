# LocalMart storefront

This folder contains the responsive browser frontend for the LocalMart FastAPI
learning project. It uses plain HTML, CSS, and JavaScript; no frontend package
installation or build step is needed.

## Run the website

Start the API from the `Server` folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000/app>. FastAPI serves the frontend and API from
the same origin, so browser CORS configuration is not needed for local use.
The API documentation remains available at <http://127.0.0.1:8000/docs>.

Choose a location that has a warehouse, browse its in-stock products, then sign
in or create a customer account to use the basket, checkout, and order history.
New accounts are created for the currently selected warehouse location.

## Admin inventory demo

An existing account whose database role is `admin` sees an **Inventory**
control after sign-in. The warehouse list is restricted to warehouses whose
location exactly matches that account's saved location. The admin can review
that stock, update quantities, remove a stock record, or add stock. Product
names and prices are shared product details and cannot be edited through the
current API.

This is a UI demonstration only: the backend does not authenticate inventory
write requests or enforce admin roles. The warning is also shown in the admin
view. Do not expose this demo to untrusted users.

## Demo security note

The backend currently checks login credentials but does not issue a token or
secure session. User IDs are identifiers rather than authentication, and API
ownership/authorization checks are not implemented. This frontend keeps the
selected customer in memory only; do not use real passwords or expose this
project to untrusted users.