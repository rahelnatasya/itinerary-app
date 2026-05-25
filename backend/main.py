import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import Base, engine
from routers import router

# Reset tabel untuk development (aktifkan hanya jika RESET_DB=true)
if os.getenv("RESET_DB", "false").lower() == "true":
    Base.metadata.drop_all(bind=engine)

# Membuat tabel secara otomatis di PostgreSQL jika belum ada saat startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Collaborative Itinerary API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Backend API with PostgreSQL and Optimistic Locking is ready"}