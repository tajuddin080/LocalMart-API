from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database.connection import engine
from database.models import Base
from user_service.router import u_router
from warehouse_service.router import w_router
from order_service.router import o_router
from catalog_service.router import c_router


Base.metadata.create_all(bind=engine)


tags_metadata = [
    {
        "name": "default",
        "description": "Core system endpoints",
    },
    {
        "name": "Users",
        "description": "User management endpoints",
    },
    {
        "name":"Inventory",
        "description":"Inventory management endpoints"
    },
    {
        "name": "Catalog",
        "description": "Catalog management endpoints",
    },
    {
        "name":"Orders",
        "description":"Order management endpoints"
    }
    
]

app = FastAPI(title="Store Management System API", openapi_tags=tags_metadata)

# FIX: You must explicitly add tags=["default"] here!
@app.get("/", summary="Api root dashboard", tags=["default"])
def root():
    return {"message": "Welcome to the Store API Dashboard"}

app.include_router(u_router, tags=["Users"])
app.include_router(w_router, tags=["Inventory"])
app.include_router(o_router, tags=["Orders"])
app.include_router(c_router, tags=["Catalog"])

frontend_directory = Path(__file__).resolve().parent.parent / "client" / "static"
if frontend_directory.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=frontend_directory, html=True),
        name="frontend",
    )