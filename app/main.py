from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine, Base, SessionLocal
from app.routers import resources
from app.routers import auth as auth_router

load_dotenv()


def _seed_admin():
    from app.models import User
    from app.auth_utils import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "ben@groovemarketing.co.uk").first():
            admin = User(
                first_name="Ben",
                last_name="Henderson",
                email="ben@groovemarketing.co.uk",
                school="Groove Marketing",
                key_stages="[]",
                hashed_password=hash_password("     "),
                role="admin",
                is_school_verified=True,
                is_active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_admin()
    yield


app = FastAPI(
    title="Resource Builder",
    description="Educational resource generation engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router.router)
app.include_router(resources.router)
