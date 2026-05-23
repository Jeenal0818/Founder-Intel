# scripts/init_db.py
# Initialize the database on startup
from founder_intel_agent.app.db import Base, engine
from app import models  # noqa: F401  (ensures models are imported)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

from sqlalchemy import create_engine
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)
